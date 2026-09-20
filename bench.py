#!/usr/bin/env python3
"""Benchmark retrieval trên corpus data/ecommerce.

Đọc từng file .md, tách front matter thành metadata và phần thân thành content,
chunk phần thân ở TẦNG NGOÀI store, nạp vào EmbeddingStore rồi chạy 5 benchmark
query. Chấm ở hai mức: doc_id có trong top-3 chưa, và ngữ cảnh truy xuất được có
thật sự chứa đáp án không.

    python bench.py                  # in ra màn hình
    python bench.py -o ket_qua_benchmark.txt
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from src.chunking import FixedSizeChunker, RecursiveChunker, SentenceChunker
from src.embeddings import (
    EMBEDDING_PROVIDER_ENV,
    GEMINI_EMBEDDING_MODEL,
    LOCAL_EMBEDDING_MODEL,
    OPENAI_EMBEDDING_MODEL,
    GeminiEmbedder,
    LocalEmbedder,
    OpenAIEmbedder,
    _mock_embed,
)
from src.models import Document
from src.store import EmbeddingStore

DATA_DIR = Path("data/ecommerce")
TOP_K = 3
CACHE_PATH = Path(".embed_cache.json")


class CachedEmbedder:
    """Cache embedding theo hash nội dung + retry khi bị rate limit.

    API trả tiền/có quota thì gọi lại cùng một chunk là lãng phí: corpus 157
    chunk chạy lại vài lần là chạm giới hạn free tier. Cache ghi ra đĩa nên
    lần chạy sau gần như không tốn lượt gọi nào.
    """

    def __init__(self, embedder, backend: str, cache_path: Path = CACHE_PATH,
                 max_retries: int = 5) -> None:
        self._embedder = embedder
        self._backend = backend
        self._backend_name = backend
        self._cache_path = cache_path
        self._max_retries = max_retries
        self.hits = self.misses = 0
        try:
            self._cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            self._cache = {}

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self._backend}\x00{text}".encode()).hexdigest()

    def __call__(self, text: str) -> list[float]:
        key = self._key(text)
        if key in self._cache:
            self.hits += 1
            return self._cache[key]

        self.misses += 1
        delay = 2.0
        for attempt in range(1, self._max_retries + 1):
            try:
                vector = self._embedder(text)
                break
            except Exception as error:
                if attempt == self._max_retries:
                    raise
                print(
                    f"  [retry {attempt}/{self._max_retries}] {type(error).__name__}; "
                    f"cho {delay:.0f}s roi thu lai...",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= 2

        self._cache[key] = vector
        return vector

    def save(self) -> None:
        try:
            self._cache_path.write_text(json.dumps(self._cache), encoding="utf-8")
        except Exception as error:
            print(f"  [canh bao] khong ghi duoc cache: {error}", file=sys.stderr)


class HeadingChunker:
    """Chia nhỏ theo tiêu đề/mục của văn bản chính sách.

    Lý do thiết kế: văn bản quy định được người soạn chia sẵn theo mục
    (`## 3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG/HOÀN TIỀN`), mỗi mục đã là một đơn vị
    ngữ nghĩa trọn vẹn. Cắt theo ranh giới đó giữ được trọn điều khoản thay vì
    cắt ngang giữa câu như fixed-size.

    Mục nào dài quá `chunk_size` thì hạ xuống RecursiveChunker, và **gắn lại
    tiêu đề vào từng mảnh con** — không có nó thì từ mảnh thứ hai trở đi mất
    ngữ cảnh "đây là mục nói về cái gì".
    """

    HEADING = re.compile(r"^#{1,6} .*$", re.M)

    def __init__(self, chunk_size: int = 800) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []

        sections = [s.strip() for s in re.split(r"(?=^#{1,6} )", text, flags=re.M) if s.strip()]
        if not sections:
            sections = [text.strip()]

        chunks: list[str] = []
        for section in sections:
            if len(section) <= self.chunk_size:
                chunks.append(section)
                continue

            lines = section.split("\n")
            heading = lines[0] if self.HEADING.match(lines[0]) else ""
            body = "\n".join(lines[1:]) if heading else section
            for piece in self._fallback.chunk(body):
                chunks.append(f"{heading}\n{piece}".strip() if heading else piece)
        return chunks


# ---------------------------------------------------------------------------
# ĐỔI ĐÚNG MỘT DÒNG NÀY sang chiến lược của bạn. Mọi thứ khác giữ nguyên để so
# sánh giữa các thành viên mới công bằng.
#   FixedSizeChunker(chunk_size=800, overlap=100) | SentenceChunker(5)
#   RecursiveChunker(chunk_size=800)              | HeadingChunker(chunk_size=800)
CHUNKER = HeadingChunker(chunk_size=800)
CHUNKER_NAME = "HeadingChunker(chunk_size=800)"
# ---------------------------------------------------------------------------

# Dùng cho `--strategy <ten>` và `--strategy all` (so sánh 4 chiến lược).
# Tham số chọn sao cho cùng ngưỡng 800 ký tự, để so sánh mới công bằng.
STRATEGIES: dict[str, tuple] = {
    "fixed_size": (lambda: FixedSizeChunker(chunk_size=800, overlap=100),
                   "FixedSizeChunker(chunk_size=800, overlap=100)"),
    "by_sentences": (lambda: SentenceChunker(max_sentences_per_chunk=5),
                     "SentenceChunker(max_sentences_per_chunk=5)"),
    "recursive": (lambda: RecursiveChunker(chunk_size=800),
                  "RecursiveChunker(chunk_size=800)"),
    "heading": (lambda: HeadingChunker(chunk_size=800),
                "HeadingChunker(chunk_size=800)"),
}


# 5 benchmark query nhóm thống nhất (xem report/REPORT_NHOM.md mục 3).
# `must_contain` là chuỗi đặc trưng phải xuất hiện trong ngữ cảnh truy xuất được
# — chấm theo doc_id không thôi sẽ thổi phồng kết quả.
QUERIES = [
    {
        "id": 1,
        "kind": "tra số liệu",
        "question": "Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng hoàn tiền "
                    "kể từ khi đơn hàng được cập nhật giao hàng thành công?",
        "gold_doc_id": "shopee-return-refund-buyer",
        "must_contain": "15 (mười lăm) ngày",
        "metadata_filter": None,
    },
    {
        "id": 2,
        "kind": "hỏi điều kiện",
        "question": "Đơn hàng ở trạng thái nào thì người mua hủy được ngay, "
                    "trạng thái nào phải chờ người bán phản hồi?",
        "gold_doc_id": "shopee-buyer-cancel-order",
        "must_contain": "Chờ xác nhận",
        "metadata_filter": None,
    },
    {
        "id": 3,
        "kind": "hỏi quy trình — CẦN FILTER",
        # Cố ý KHÔNG nêu rõ ai hỏi: corpus có hai tài liệu cùng chủ đề trả hàng,
        # cùng từ vựng, khác đối tượng và khác đáp án (15 ngày với người mua,
        # 02 ngày lịch với người bán). Không lọc thì top-3 lẫn cả hai.
        "question": "Thời hạn xử lý một yêu cầu trả hàng là bao nhiêu ngày?",
        "gold_doc_id": "shopee-return-refund-seller",
        "must_contain": "02 ngày lịch",
        "metadata_filter": {"audience": "seller"},
    },
    {
        "id": 4,
        "kind": "liệt kê",
        "question": "Sản phẩm hoàn trả phải đáp ứng những yêu cầu gì khi người mua gửi trả?",
        "gold_doc_id": "shopee-return-refund-buyer",
        "must_contain": "hóa đơn thuế GTGT",
        "metadata_filter": None,
    },
    {
        "id": 5,
        "kind": "tra số liệu",
        "question": "Hàng hóa phải còn hạn sử dụng bao lâu thì người bán mới được đăng bán?",
        "gold_doc_id": "shopee-seller-listing-rules",
        "must_contain": "ít nhất 30%",
        "metadata_filter": None,
    },
]


def parse_front_matter(raw: str) -> tuple[dict[str, str], str]:
    """Tách front matter thành metadata, phần còn lại thành content."""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta = dict(re.findall(r"^(\w+):\s*(.+?)\s*$", parts[1], re.M))
    # Bỏ ngoặc kép nếu có: metadata_filter so sánh bằng == nên 'seller' khác '"seller"'.
    return {k: v.strip().strip('"') for k, v in meta.items()}, parts[2].strip()


def build_documents(chunker) -> tuple[list[Document], dict[str, int]]:
    documents: list[Document] = []
    per_file: dict[str, int] = {}

    for path in sorted(DATA_DIR.glob("*.md")):
        metadata, content = parse_front_matter(path.read_text(encoding="utf-8"))
        chunks = chunker.chunk(content)
        per_file[path.stem] = len(chunks)
        for index, chunk in enumerate(chunks):
            documents.append(
                Document(
                    id=f"{path.stem}#{index}",
                    content=chunk,
                    # Trải toàn bộ front matter vào MỌI chunk, nếu không
                    # search_with_filter() không có gì để lọc. doc_id trỏ về
                    # file gốc, còn Document.id mới là "file#0".
                    metadata={**metadata, "doc_id": path.stem, "chunk_index": index},
                )
            )
    return documents, per_file


def pick_embedder():
    load_dotenv(override=False)
    provider = os.getenv(EMBEDDING_PROVIDER_ENV, "mock").strip().lower()
    builders = {
        "local": lambda: LocalEmbedder(os.getenv("LOCAL_EMBEDDING_MODEL", LOCAL_EMBEDDING_MODEL)),
        "openai": lambda: OpenAIEmbedder(os.getenv("OPENAI_EMBEDDING_MODEL", OPENAI_EMBEDDING_MODEL)),
        "gemini": lambda: GeminiEmbedder(os.getenv("GEMINI_EMBEDDING_MODEL", GEMINI_EMBEDDING_MODEL)),
    }
    if provider in builders:
        try:
            embedder = builders[provider]()
            name = getattr(embedder, "_backend_name", provider)
            # Backend thật thì bọc cache + retry; mock rẻ nên không cần.
            return CachedEmbedder(embedder, name)
        except Exception as error:
            print(f"[canh bao] Khong dung duoc backend '{provider}' ({error}); quay ve mock.")
    return _mock_embed


def grade(results: list[dict], query: dict) -> tuple[int, int | None, bool]:
    """Chấm hai mức: thứ hạng của gold doc_id, và ngữ cảnh có chứa đáp án không."""
    gold_rank = next(
        (i for i, r in enumerate(results, 1) if r["metadata"].get("doc_id") == query["gold_doc_id"]),
        None,
    )
    context = "\n".join(r["content"] for r in results)
    content_hit = query["must_contain"].lower() in context.lower()

    if gold_rank is None or not content_hit:
        points = 0
    elif gold_rank == 1:
        points = 2
    else:
        points = 1
    return points, gold_rank, content_hit


def show(results: list[dict], out) -> None:
    if not results:
        print("    (khong co ket qua)", file=out)
        return
    for rank, result in enumerate(results, 1):
        meta = result["metadata"]
        head = result["content"].split("\n")[0][:58]
        print(
            f"    {rank}. score={result['score']:+.4f}  [{meta.get('audience','?'):6}] "
            f"{meta.get('doc_id','?')}#{meta.get('chunk_index','?')}  {head}",
            file=out,
        )


def run(out, chunker=None, chunker_name: str | None = None, embedder=None) -> dict:
    """Chạy 5 query trên một chiến lược. Trả về {'total': int, 'per_query': {id: diem}}."""
    chunker = chunker or CHUNKER
    chunker_name = chunker_name or CHUNKER_NAME
    embedder = embedder or pick_embedder()
    backend = getattr(embedder, "_backend_name", embedder.__class__.__name__)

    documents, per_file = build_documents(chunker)
    store = EmbeddingStore(collection_name="bench", embedding_fn=embedder)
    store.add_documents(documents)

    print("=" * 78, file=out)
    print(f"BENCHMARK RETRIEVAL — corpus {DATA_DIR}", file=out)
    print(f"Chien luoc chunk : {chunker_name}", file=out)
    print(f"Embedding backend: {backend}", file=out)
    print("=" * 78, file=out)

    print(f"\nDa nap {store.get_collection_size()} chunk tu {len(per_file)} file:", file=out)
    for stem, count in sorted(per_file.items()):
        print(f"  {stem:34} {count:3} chunk", file=out)
    lengths = [len(d.content) for d in documents]
    print(
        f"  -> do dai chunk: min={min(lengths)} / trung binh={sum(lengths)//len(lengths)} "
        f"/ max={max(lengths)}",
        file=out,
    )

    if backend.startswith("mock"):
        print(
            "\n[CANH BAO] Dang chay MockEmbedder (bam MD5, KHONG ma hoa ngu nghia).\n"
            "           Moi diem so duoi day la nhieu, chi dung de kiem pipeline.\n"
            "           Phan tich chat luong phai dua vao count / avg_length / do mach lac.",
            file=out,
        )

    total = 0
    per_query: dict[int, int] = {}
    stats = {
        "count": len(documents),
        "avg": sum(len(d.content) for d in documents) // len(documents),
        "min": min(len(d.content) for d in documents),
        "max": max(len(d.content) for d in documents),
    }
    for query in QUERIES:
        print("\n" + "-" * 78, file=out)
        print(f"Q{query['id']} [{query['kind']}] {query['question']}", file=out)
        print(f"  gold doc_id : {query['gold_doc_id']}", file=out)
        print(f"  phai chua   : {query['must_contain']!r}", file=out)

        results = store.search_with_filter(
            query["question"], top_k=TOP_K, metadata_filter=query["metadata_filter"]
        )
        label = f"metadata_filter={query['metadata_filter']}" if query["metadata_filter"] else "khong loc"
        print(f"\n  TOP-{TOP_K} ({label}):", file=out)
        show(results, out)

        points, gold_rank, content_hit = grade(results, query)
        total += points
        per_query[query["id"]] = points
        print(
            f"\n  Cham muc doc_id : {'top-' + str(gold_rank) if gold_rank else 'VANG MAT'}\n"
            f"  Cham muc noi dung: {'CO chua dap an' if content_hit else 'KHONG chua dap an'}\n"
            f"  => {points}/2 diem",
            file=out,
        )

        # A/B bat buoc cho cau can filter.
        if query["metadata_filter"]:
            print(f"\n  --- A/B: chay lai CHINH cau nay nhung KHONG loc ---", file=out)
            unfiltered = store.search_with_filter(query["question"], top_k=TOP_K, metadata_filter=None)
            show(unfiltered, out)
            ab_points, ab_rank, ab_hit = grade(unfiltered, query)
            print(
                f"  Khong loc => {'top-' + str(ab_rank) if ab_rank else 'VANG MAT'}, "
                f"{'co' if ab_hit else 'khong'} chua dap an, {ab_points}/2 diem",
                file=out,
            )
            verdict = "FILTER CO TAC DUNG" if ab_points < points else "filter khong doi ket qua"
            print(f"  => {verdict}", file=out)

    print("\n" + "=" * 78, file=out)
    print(f"TONG: {total}/{len(QUERIES) * 2} diem", file=out)
    if isinstance(embedder, CachedEmbedder):
        embedder.save()
        print(f"Embedding cache: {embedder.hits} hit / {embedder.misses} lan goi API moi", file=out)
    print("=" * 78, file=out)
    return {"total": total, "per_query": per_query, "stats": stats, "backend": backend}


def run_all(out) -> int:
    """Chạy cả 4 chiến lược trên cùng corpus, cùng query, rồi so sánh."""
    embedder = pick_embedder()
    results: dict[str, dict] = {}

    for key, (factory, label) in STRATEGIES.items():
        print(f"\n\n{'#' * 78}\n### CHIEN LUOC: {key}\n{'#' * 78}", file=out)
        results[key] = run(out, factory(), label, embedder)

    print("\n\n" + "=" * 78, file=out)
    print("SO SANH 4 CHIEN LUOC — cung corpus, cung 5 query, cung backend", file=out)
    print("=" * 78, file=out)
    header = f"{'chien luoc':14} {'chunk':>6} {'min':>5} {'tb':>5} {'max':>6}  " + \
             "  ".join(f"Q{q['id']}" for q in QUERIES) + f"  {'TONG':>6}"
    print(header, file=out)
    print("-" * len(header), file=out)
    for key, data in sorted(results.items(), key=lambda kv: -kv[1]["total"]):
        s = data["stats"]
        cells = "  ".join(f"{data['per_query'][q['id']]} " for q in QUERIES)
        print(f"{key:14} {s['count']:6} {s['min']:5} {s['avg']:5} {s['max']:6}  "
              f"{cells}  {data['total']:>4}/10", file=out)
    print("\n(Q3 la cau co metadata_filter; diem tinh theo muc noi dung, "
          "2d = gold top-1 + ngu canh chua dap an)", file=out)
    if isinstance(embedder, CachedEmbedder):
        embedder.save()
        print(f"\nEmbedding cache tong: {embedder.hits} hit / {embedder.misses} lan goi API moi", file=out)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", type=Path, help="Ghi ket qua ra file")
    parser.add_argument(
        "-s", "--strategy", default=None,
        choices=[*STRATEGIES, "all"],
        help="Chay mot chien luoc cu the, hoac 'all' de so sanh ca 4 "
             "(mac dinh: dung bien CHUNKER trong file)",
    )
    args = parser.parse_args()

    if not DATA_DIR.is_dir():
        print(f"Khong thay thu muc corpus: {DATA_DIR}", file=sys.stderr)
        return 2

    def dispatch(handle) -> int:
        if args.strategy == "all":
            return run_all(handle)
        if args.strategy:
            factory, label = STRATEGIES[args.strategy]
            run(handle, factory(), label)
            return 0
        run(handle)
        return 0

    if args.output:
        with args.output.open("w", encoding="utf-8") as handle:
            code = dispatch(handle)
        print(f"Da ghi {args.output}")
        return code
    return dispatch(sys.stdout)


if __name__ == "__main__":
    raise SystemExit(main())
