# Báo Cáo Nhóm — Lab 7: Embedding & Vector Store

**Nhóm:** fanboiPNV
**Thành viên:** Nguyễn Minh Quân · Nguyễn Thành Nam · Hoàng Anh Tú · Đinh Bảo Hưng
**Ngày:** 20/09/2026

> **Nộp 1 bản / nhóm.** Phần cá nhân (hướng tiếp cận, kết quả riêng, dự đoán…) mỗi thành viên nộp riêng trong `REPORT_CANHAN.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần nhóm: 40** = Lựa chọn tài liệu (10) + Thiết kế chiến lược (15) + Chất lượng truy xuất (10) + Thuyết trình (5).

---

## 1. Lựa chọn tài liệu (Document Set Quality) — Nhóm (10 điểm)

### Chủ đề (Domain) & Lý Do Chọn

**Chủ đề:** Chính sách đổi trả, hoàn tiền và quy định người bán/người mua trên sàn thương mại điện tử Shopee Việt Nam (chủ đề bắt buộc của lớp K4-L3B — xem `K4_VARIANT.md`).

**Tại sao nhóm chọn chủ đề này?**
> Chủ đề là bắt buộc với lớp L3B, nhưng trong phạm vi đó nhóm chọn **Shopee Việt Nam** vì ba lý do đo được. Thứ nhất, toàn bộ chính sách nằm trên Trung tâm trợ giúp công khai, `robots.txt` cho phép, nên không vướng ràng buộc quản trị dữ liệu. Thứ hai, chủ đề này có sẵn **hai đối tượng đối lập** (`buyer` / `seller`) cùng bàn về một việc nhưng khác đáp án — điều kiện cần để `metadata_filter` có việc thật, mà nhiều chủ đề khác không có. Thứ ba, văn bản được soạn theo điều khoản đánh số (`3.2.`, `## D.`), tạo ranh giới tự nhiên cho chiến lược chunk theo heading mà `K4_VARIANT.md` yêu cầu ít nhất một thành viên phải thử.

### Danh sách tài liệu (Data Inventory)

Corpus gồm 7 tài liệu, thu thập ngày 2026-09-20 từ Trung tâm trợ giúp Shopee bằng `scripts/fetch_public_pages.py`, đã làm sạch thủ công trước khi dùng làm benchmark.

| # | Tên tài liệu | Nguồn (Source URL) | Ngày lấy / Phiên bản | Số ký tự | Metadata đã gán |
|---|--------------|------------|--------------------|----------|-----------------|
| 1 | Chính sách Trả hàng và Hoàn tiền — quyền và nghĩa vụ Người Mua | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / 2026-03-11 | 16.400 | `audience: buyer`, `category: returns-policy`, `language: vi` |
| 2 | Chính sách Trả hàng và Hoàn tiền — trách nhiệm Người Bán | https://help.shopee.vn/portal/4/article/77251 | 2026-09-20 / 2026-03-11 | 2.525 | `audience: seller`, `category: returns-policy`, `language: vi` |
| 3 | Quy định hủy đơn hàng dành cho Người Mua | https://help.shopee.vn/portal/4/article/79182 | 2026-09-20 / not-stated | 1.967 | `audience: buyer`, `category: order-policy`, `language: vi` |
| 4 | Quy định đăng bán sản phẩm dành cho Người Bán | https://help.shopee.vn/portal/4/article/77246 | 2026-09-20 / 2024-08-14 | 20.762 | `audience: seller`, `category: seller-rules`, `language: vi` |
| 5 | Chính sách vận chuyển và đồng kiểm hàng hóa | https://help.shopee.vn/portal/4/article/77250 | 2026-09-20 / 2026-09-15 | 23.666 | `audience: both`, `category: shipping-policy`, `language: vi` |
| 6 | Chính sách chung về Mã Ưu Đãi (Voucher) Shopee | https://help.shopee.vn/portal/4/article/166085 | 2026-09-20 / 2026-05-23 | 11.308 | `audience: buyer`, `category: promotion-policy`, `language: vi` |
| 7 | Chính sách hàng hóa cấm và hạn chế bán | https://help.shopee.vn/portal/4/article/77247 | 2026-09-20 / 2025-04-28 | 12.462 | `audience: seller`, `category: product-compliance`, `language: vi` |

Phân bố `audience`: **buyer 3 · seller 3 · both 1**. Số ký tự tính phần thân, không tính front matter.

**Hai tài liệu số 1 và 2 tách ra từ cùng một trang nguồn.** Trang gốc (article 77251) gộp thời hạn của người mua (15 ngày, §3.2) lẫn thời hạn phản hồi của người bán (02 ngày lịch, §5) trong một văn bản. Nếu lưu thành một file `audience: both` thì `metadata_filter={"audience":"seller"}` không lọc được gì vì hai đáp án nằm chung tài liệu. Tách đôi theo điều khoản, giữ nguyên số mục gốc (§5, §7 sang file người bán) để gold answer trích dẫn được. Cùng lý do, khối §10–12 (đồng tài trợ mã ưu đãi, chỉ áp dụng Người Bán) đã được gỡ khỏi tài liệu số 6 để nhãn `buyer` khớp với nội dung thật.

**Danh sách kiểm tra quản trị dữ liệu (Data governance checklist):**
- [x] Tập tài liệu (Corpus) chỉ chứa nguồn công khai/được phép dùng và không chứa dữ liệu cá nhân, thông tin đăng nhập hoặc tài liệu nội bộ.
- [x] Mỗi tài liệu có `source_url`, `retrieved_at`, `document_version` (hoặc ngày hiệu lực) trong metadata.

`document_version` lấy từ dòng hiệu lực ghi trong chính văn bản nguồn (ví dụ "có hiệu lực kể từ ngày 11/3/2026"). Riêng tài liệu số 3 nguồn không nêu ngày nên để `not-stated`, không suy đoán.

### Cấu trúc Metadata (Metadata Schema)

| Trường metadata | Kiểu | Ví dụ giá trị | Tại sao hữu ích cho truy xuất (retrieval)? |
|----------------|------|---------------|-------------------------------|
| `doc_id` | string | `shopee-return-refund-seller` | Khóa ổn định trỏ về file gốc. `delete_document()` xóa theo trường này, và khi chunk thì `Document.id` là `"file#0"` còn `doc_id` vẫn trỏ về tài liệu nên đối chiếu benchmark được. |
| `audience` | enum `buyer`/`seller`/`both` | `seller` | Trường lọc chính. Corpus có hai tài liệu cùng chủ đề trả hàng, cùng từ vựng, khác đối tượng và khác đáp án — không lọc thì top-3 lẫn hai bên và agent trả lời sai đối tượng. |
| `category` | enum | `returns-policy` | Thu hẹp theo loại chính sách khi câu hỏi đã rõ chủ đề (đổi trả / vận chuyển / hàng cấm), tránh kéo về chính sách khác cùng nói "hoàn tiền". |
| `language` | ISO 639-1 | `vi` | Toàn corpus hiện là `vi`. Giữ sẵn để nếu bổ sung tài liệu tiếng Anh thì lọc được, tránh mô hình đa ngữ trộn hai ngôn ngữ. |
| `source_url` | URL | `https://help.shopee.vn/portal/4/article/77251` | Truy vết nguồn cho từng câu trả lời (tiêu chí *Source Traceability* trong `docs/EVALUATION.md`). |
| `retrieved_at` | date | `2026-09-20` | Biết dữ liệu cũ tới đâu khi chính sách nguồn thay đổi. |
| `document_version` | date hoặc `not-stated` | `2026-03-11` | Phân biệt phiên bản chính sách; khi hai tài liệu mâu thuẫn thì biết bản nào mới hơn. |

**Lưu ý khi nạp:** front matter phải để **không có dấu ngoặc kép**. Crawler `scripts/fetch_public_pages.py` bọc mọi giá trị bằng `"..."` (hàm `yaml_value`), khiến `metadata['audience']` đọc ra là `'"seller"'` chứ không phải `'seller'` — lúc đó `metadata_filter={"audience": "seller"}` không khớp gì và `search_with_filter()` luôn trả rỗng. Script kiểm tra ở mục 6 của `docs/DATA_COLLECTION.md` cũng báo `THIEU METADATA` vì `doc_id` đọc ra kèm ngoặc kép nên không bằng tên file.

---

## 2. Thiết kế chiến lược (Strategy Design) — Nhóm (15 điểm)

> Mỗi thành viên thử **một chiến lược khác nhau** trên cùng bộ tài liệu; nhóm tổng hợp và so sánh ở đây.

### Phân tích đường cơ sở (Baseline Analysis)

Chạy `ChunkingStrategyComparator().compare()` trên 2-3 tài liệu:

Chạy `ChunkingStrategyComparator().compare(body, chunk_size=800)` trên 3 tài liệu, **đã bỏ front matter** trước khi đo (nếu không là đang đo cả khối YAML). Cột `min`/`max` thêm vào để thấy độ đồng đều, vì `avg_length` một mình che mất sự lệch.

| Tài liệu | Chiến lược (Strategy) | Số lượng Chunk | Độ dài trung bình | min / max | Giữ được ngữ cảnh không? |
|-----------|----------|-------------|------------|-----------|-------------------|
| return-refund-buyer | FixedSizeChunker (`fixed_size`) | 21 | 780 | 400 / 800 | ❌ Đều nhất nhưng cắt ngang câu và ngang điều khoản |
| return-refund-buyer | SentenceChunker (`by_sentences`) | 41 | 397 | 44 / 902 | ⚠️ Câu trọn vẹn nhưng vụn; số hiệu điều khoản (`3.2.`) bị tách thành chunk mồ côi |
| return-refund-buyer | RecursiveChunker (`recursive`) | 25 | 654 | 181 / 793 | ✅ Cân bằng tốt, cắt theo đoạn trước |
| return-refund-buyer | **HeadingChunker** (custom) | 29 | 593 | 64 / 850 | ✅ Mỗi chunk là một điều khoản trọn vẹn |
| buyer-cancel-order | FixedSizeChunker (`fixed_size`) | 3 | 655 | 367 / 800 | ❌ Cắt đôi bảng trạng thái đơn hàng |
| buyer-cancel-order | SentenceChunker (`by_sentences`) | 5 | 392 | 104 / 705 | ⚠️ Bảng Markdown bị coi là một "câu" dài |
| buyer-cancel-order | RecursiveChunker (`recursive`) | 3 | 654 | 591 / 732 | ✅ Đều nhưng gộp nhiều mục |
| buyer-cancel-order | **HeadingChunker** (custom) | 7 | 279 | 42 / 790 | ✅ Tách đúng 4 mục + mục con 2.1/2.2 |
| shipping-policy | FixedSizeChunker (`fixed_size`) | 30 | 788 | 466 / 800 | ❌ Cắt ngang danh sách hàng cấm vận chuyển |
| shipping-policy | SentenceChunker (`by_sentences`) | 61 | 383 | 110 / 1229 | ⚠️ Lệch nhất: có chunk 110 ký tự, có chunk 1.229 |
| shipping-policy | RecursiveChunker (`recursive`) | 37 | 637 | 185 / 798 | ✅ Ổn định nhất về kích thước |
| shipping-policy | **HeadingChunker** (custom) | 43 | 574 | 34 / 867 | ✅ Bám mục A–E và mục con, nhưng sinh chunk 34 ký tự ở mục quá ngắn |

**Nhận xét:** `fixed_size` cho kích thước đều nhất (min/max sát nhau) nhưng ranh giới vô nghĩa về ngữ pháp. `by_sentences` lệch nhất — trên `shipping-policy` chênh 110–1.229 ký tự, vì bảng Markdown và danh sách gạch đầu dòng không có dấu chấm nên bị gom thành một "câu" khổng lồ. `recursive` là mặc định an toàn. `HeadingChunker` bám cấu trúc điều khoản tốt nhất nhưng có nhược điểm thật: mục nào ngắn (chỉ một dòng tiêu đề + một câu) sẽ thành chunk 34–64 ký tự gần như vô dụng khi truy xuất — cần gom mục quá ngắn vào mục kế tiếp, hiện chưa làm.

### Chiến lược của từng thành viên

> Mỗi thành viên điền một khối dưới đây (copy thêm nếu nhóm có nhiều hơn 3 người).

**Thành viên 1 — Nguyễn Minh Quân** *(chiến lược đã chạy và có số liệu đầy đủ)*
- **Loại chiến lược:** custom — `HeadingChunker`
- **Mô tả & lý do chọn cho chủ đề này:** Văn bản quy định đã được người soạn chia sẵn theo mục (`## 3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG/HOÀN TIỀN`), mỗi mục là một đơn vị ngữ nghĩa trọn vẹn. Cắt theo ranh giới có sẵn đó thay vì áp một kích thước cố định lên trên. Mục nào dài quá ngưỡng thì hạ xuống `RecursiveChunker` và **gắn lại tiêu đề vào từng mảnh con** — không có bước đó thì từ mảnh thứ hai trở đi mất ngữ cảnh "đây là mục nói về cái gì".
- **Code snippet:**
```python
class HeadingChunker:
    HEADING = re.compile(r"^#{1,6} .*$", re.M)

    def __init__(self, chunk_size: int = 800) -> None:
        self.chunk_size = chunk_size
        self._fallback = RecursiveChunker(chunk_size=chunk_size)

    def chunk(self, text: str) -> list[str]:
        if not text or not text.strip():
            return []
        # Lookahead: dòng heading không bị nuốt, nó mở đầu chunk của chính nó.
        sections = [s.strip() for s in re.split(r"(?=^#{1,6} )", text, flags=re.M) if s.strip()]
        chunks = []
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
```

**Thành viên 2 — Nguyễn Thành Nam**
- **Loại chiến lược:** custom — `MarkdownHeadingChunker` + lọc metadata
- **Mô tả & lý do chọn:** Cùng ý tưởng bám heading, nhưng nhấn vào việc **bảo toàn ngữ cảnh điều khoản cha cho mọi mảnh con** khi phải cắt nhỏ một mục dài. Chạy trên `MockEmbedder`, kết quả 1/5 câu có chunk liên quan trong top-3 — bạn tự ghi nhận nguyên nhân là nhiễu hàm băm chứ không phải lỗi chiến lược, và chuyển trọng tâm đánh giá sang độ mạch lạc của chunk.
- **Lưu ý đối chiếu:** chạy trên **snapshot corpus cũ** (còn `shopee-terms-of-service`, `shopee-operation-regulations` — hai tài liệu sau đó đã bị loại khỏi corpus vì ngoài phạm vi). Điều này giải thích vì sao top-1 của câu 1 và câu 3 rơi vào `shopee-terms-of-service`.

**Thành viên 3 — Hoàng Anh Tú**
- **Loại chiến lược:** *(chưa chốt — báo cáo cá nhân mới có mục 1–3, chưa có mục 4 và 5)*
- **Mô tả & lý do chọn:** Phần code đã hoàn thiện đầy đủ (42 passed) với cách tiếp cận trùng khớp cả nhóm: regex lookbehind cho `SentenceChunker`, thuật toán hai chiều cho `RecursiveChunker`, tiền lọc (pre-filtering) cho `search_with_filter`, prompt đánh số `[1] [2]` kèm nguồn cho agent. **Chưa chạy benchmark nên chưa có số liệu để đưa vào bảng so sánh.**

**Thành viên 4 — Đinh Bảo Hưng**
- **Loại chiến lược:** custom — `HeadingChunker(chunk_size=800)`, cài đặt trong workspace riêng của bạn ấy (`src/heading_chunking.py` ở repo của Đinh Bảo Hưng, không có trong repo này)
- **Mô tả & lý do chọn:** Giữ **toàn bộ đường dẫn heading** (không chỉ heading gần nhất) trong từng mảnh con, với ngân sách `800 − độ dài đường dẫn heading − xuống dòng`. Lý do: trong tài liệu nguồn, cùng một mục "Stripe" xuất hiện ở cả hoàn tiền toàn bộ lẫn hoàn tiền một phần, chỉ đường dẫn heading mới phân biệt được.
- **Lưu ý đối chiếu:** chạy trên **corpus hoàn toàn khác** — tài liệu Open Food Network tiếng Anh, 5 file → 114 chunk (36 buyer / 78 seller), backend `MockEmbedder 64D`, và **bộ 5 query riêng bằng tiếng Anh** (Stripe refund, subscription…). Đạt 5/5 nhưng trên bộ đề của chính mình.

### So Sánh Giữa Các Thành Viên

#### 3a. So sánh giữa các thành viên — và vì sao nó KHÔNG so trực tiếp được

| Thành viên | Chiến lược | Corpus | Backend | Bộ query | Điểm tự báo |
|---|---|---|---|---|---|
| Nguyễn Minh Quân | `HeadingChunker(800)` | Shopee, 7 file (bản đã lọc) | **gemini-embedding-001** | Bộ VN 5 câu | **10/10** |
| Nguyễn Thành Nam | `MarkdownHeadingChunker` | Shopee, **snapshot cũ** (còn 2 file đã loại) | MockEmbedder | Bộ VN khác | **1/5** |
| Hoàng Anh Tú | *(chưa chốt)* | — | — | — | *(chưa chạy)* |
| Đinh Bảo Hưng | `HeadingChunker(800)` | **Open Food Network, tiếng Anh**, 5 file / 114 chunk | MockEmbedder 64D | **Bộ EN riêng** | **5/5** |

**Bốn điều kiện đã lệch nhau, nên cột "điểm tự báo" không dùng để xếp hạng được:**

1. **Ba corpus khác nhau.** Lab yêu cầu cả nhóm dùng chung một bộ tài liệu; thực tế có Shopee bản mới, Shopee bản cũ, và một corpus tiếng Anh hoàn toàn khác chủ đề lớp L3B.
2. **Ba bộ query khác nhau.** `docs/SCORING.md` nói rõ *"Nhóm thống nhất 5 câu hỏi đánh giá"* — điều kiện để so sánh có nghĩa. Hiện mỗi người chấm trên đề của mình, nên 10/10, 5/5 và 1/5 đo ba thứ khác nhau.
3. **Backend khác nhau.** Chỉ một người chạy embedder thật. Chênh lệch giữa mock và thật đã đo được là **0/10 vs 10/10** trên cùng chiến lược, cùng corpus — lớn hơn mọi khác biệt giữa các chiến lược.
4. **Chiến lược trùng nhau.** Ba trên bốn người đều chọn biến thể chunk-theo-heading, trong khi lab dặn *"Chiến lược chunking không được trùng nhau"*. Nhóm vô tình mất đi phần lớn không gian so sánh.

Điểm chung đáng ghi nhận: cả bốn báo cáo đều **42 passed**, và ba người mô tả `search_with_filter` bằng đúng cơ chế tiền lọc (pre-filtering) — phần code cốt lõi thì nhóm đồng nhất.

#### 3b. So sánh có kiểm soát — 4 chiến lược, cùng mọi điều kiện

> Vì 3a không cho kết luận được, chúng tôi chạy thêm một phép đo **có kiểm soát**: cả 4 chiến lược trên **cùng corpus, cùng 5 query, cùng backend `gemini-embedding-001`, cùng `top_k=3`** — chỉ đổi đúng một dòng chọn chunker trong `bench.py`. Kết quả đầy đủ ở `ket_qua_4_chien_luoc.txt`, chạy bằng `python bench.py --strategy all`.

| Chiến lược | Điểm truy xuất (/10) | Chunk | min / tb / max | Cắt giữa câu | Điểm mạnh | Điểm yếu |
|-----------|----------------------|-------|----------------|--------------|-----------|----------|
| `fixed_size` (800, overlap 100) | **10** | 130 | 108 / 779 / 800 | **83%** | Ít chunk nhất, kích thước đều nhất, rẻ nhất khi embed | Ranh giới vô nghĩa: top-1 của Q1 bắt đầu bằng `"thuận này)."`, top-1 của Q5 bắt đầu bằng dấu chấm |
| `by_sentences` (5 câu) | **10** | 165 | 110 / 536 / **1619** | 19% | Chunk luôn là câu trọn vẹn, dễ đọc khi kiểm thủ công | Lệch kích thước nhất (chênh 15×): bảng Markdown và danh sách gạch đầu dòng không có dấu chấm nên bị gom thành một "câu" 1.619 ký tự |
| `recursive` (800) | **10** | 136 | 85 / 653 / 798 | 46% | Cân bằng tốt nhất giữa kích thước và ngữ nghĩa; gap top1–top2 ở Q3 rộng nhất (+0,0453) nên xếp hạng dứt khoát nhất | Vẫn cắt giữa câu gần một nửa số chunk |
| **`HeadingChunker` (800)** | **10** | 157 | **34** / 596 / 867 | **0%** | **Không chunk nào cắt giữa câu; 100% chunk mang theo tiêu đề mục** nên truy vết được về đúng điều khoản | 10 chunk dưới 120 ký tự, có cái chỉ là dòng tiêu đề 42 ký tự — chúng chiếm top-1 ở Q2 và Q3 dù chứa 0 dữ kiện |

**Chiến lược nào tốt nhất cho chủ đề này? Tại sao?**
> **Trước hết phải nói kết quả điểm là vô dụng để so sánh: cả 4 chiến lược đều 10/10.** Với embedder thật, 5 benchmark query của nhóm quá dễ — chiến lược nào cũng đưa được gold chunk lên top-1. Đây là một **benchmark bão hoà**, và nếu chỉ nhìn cột điểm thì chúng tôi đã kết luận sai rằng "chọn gì cũng như nhau".
>
> Khác biệt thật nằm ở **độ mạch lạc của chunk**, đo bằng tỉ lệ chunk bị cắt giữa câu: `fixed_size` **83%**, `recursive` 46%, `by_sentences` 19%, `HeadingChunker` **0%**. Cùng đạt 2/2 điểm ở Q1, nhưng top-1 của `fixed_size` là `"thuận này).\n\nSản Phẩm ở trạng thái nguyên vẹn…"` — một mảnh bắt đầu bằng nửa vế câu — trong khi top-1 của `HeadingChunker` là `"## 3. ĐIỀU KIỆN YÊU CẦU TRẢ HÀNG/HOÀN TIỀN\n…"`, trọn vẹn và tự khai báo mình thuộc điều khoản nào. Với corpus là văn bản quy định thì khác biệt này quan trọng hơn điểm số: người đọc phải kiểm được câu trả lời dựa trên điều khoản nào, tức tiêu chí *Source Traceability* trong `docs/EVALUATION.md`.
>
> **Chọn `HeadingChunker`**, với một điều kiện: phải bổ sung bước gom chunk ngắn. Hiện 10/157 chunk dưới 120 ký tự và chúng chiếm top-1 ở Q2, Q3 dù không chứa dữ kiện nào — ba câu đó chỉ được điểm nhờ chunk xếp thứ 2–3. **Nếu `top_k=1` thì `HeadingChunker` mất 6/10 còn `recursive` vẫn giữ nguyên**, vì `recursive` không sinh chunk tiêu đề rỗng. Nói cách khác: `HeadingChunker` thắng về chất lượng ranh giới, nhưng đang nợ đúng một bước mà `RecursiveChunker` đã làm sẵn — gom mảnh nhỏ liền kề tới sát `chunk_size`.
>
> **Nếu đổi sang chủ đề khác** (FAQ, tài liệu kỹ thuật không đánh số mục), `HeadingChunker` sẽ mất lợi thế ngay vì không còn heading để bám — lúc đó `recursive` là lựa chọn mặc định an toàn nhất, và đó cũng là câu trả lời cho câu hỏi giảng viên hay hỏi "chuyển chủ đề thì chiến lược nào còn dùng được".

---

## 3. Câu hỏi đánh giá & Chất lượng truy xuất (Retrieval Quality) — Nhóm (10 điểm)

### Câu hỏi đánh giá & Câu trả lời chuẩn (nhóm thống nhất)

> **Đúng 5 câu hỏi**, đa dạng, có thể kiểm chứng; **ít nhất 1 câu** cần lọc metadata mới trả lời tốt. Đây là bộ câu hỏi chung cho mọi thành viên chạy.

| # | Câu hỏi (Query) | Câu trả lời chuẩn (Gold Answer) | Chunk nào chứa thông tin? |
|---|-------|-------------------------------|--------------------------|
| 1 | Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng/hoàn tiền kể từ khi đơn hàng được cập nhật giao hàng thành công? | 15 (mười lăm) ngày. Riêng thực phẩm tươi sống và đông lạnh: 24 giờ. | `shopee-return-refund-buyer.md` §3.2 |
| 2 | Đơn hàng ở trạng thái nào thì Người mua hủy được ngay, trạng thái nào phải chờ Người bán phản hồi? | Chờ xác nhận: hủy ngay. Chờ lấy hàng: cần chờ phản hồi từ Người bán (chấp nhận thì được hủy ngay, từ chối thì đơn tiếp tục giao). Các trạng thái khác: không thể yêu cầu hủy. | `shopee-buyer-cancel-order.md` §1 (bảng trạng thái) |
| 3 | **[cần `metadata_filter={"audience": "seller"}`]** Thời hạn xử lý một yêu cầu trả hàng là bao nhiêu ngày? | 02 ngày lịch kể từ ngày nhận được thông báo (áp dụng cho Người Bán). Quá thời hạn mà không phản hồi thì được hiểu là đồng ý với quyết định của Shopee. | `shopee-return-refund-seller.md` §5 |
| 4 | Sản phẩm hoàn trả phải đáp ứng những yêu cầu gì khi Người Mua gửi trả? | Đóng gói theo Chính Sách Vận Chuyển; gửi kèm toàn bộ phụ kiện, hóa đơn thuế GTGT, tem phiếu bảo hành (nếu có); sản phẩm nguyên vẹn như khi nhận; bắt buộc quay video và/hoặc chụp ảnh khi nhận hàng và khi đóng gói hoàn trả. | `shopee-return-refund-buyer.md` §6 |
| 5 | Hàng hóa phải còn hạn sử dụng bao lâu thì Người Bán mới được phép đăng bán? | Khi giao đi phải còn ít nhất 30% thời hạn sử dụng **và** còn ít nhất 30 ngày tính đến ngày hết hạn. | `shopee-seller-listing-rules.md` §D |

**Vì sao câu 3 cần lọc metadata:** câu 1 và câu 3 dùng gần như cùng bộ từ vựng ("yêu cầu trả hàng", "bao nhiêu ngày") nhưng khác đối tượng và khác đáp án (15 ngày với người mua, 02 ngày lịch với người bán). Câu 3 **cố ý không nêu rõ ai hỏi**, nên nếu không lọc thì retrieval lẫn hai tài liệu và agent trả lời sai đối tượng. Đã kiểm bằng A/B thật, xem mục dưới.

> **Bài học khi thiết kế câu này:** phiên bản đầu chúng tôi viết *"…**bên bán** có bao lâu để gửi phản hồi?"* — nêu thẳng đối tượng. A/B cho kết quả **giống hệt nhau** ở cả hai lần (đều 2/2), tức câu hỏi chưa thực sự cần filter vì embedder đã tự tìm đúng tài liệu nhờ từ "bên bán". Phải sửa câu hỏi cho mơ hồ về đối tượng thì filter mới có việc thật.

### Tổng hợp chất lượng truy xuất của nhóm

> Cách chấm (theo `docs/SCORING.md`): **2 điểm/câu** — top-3 chứa chunk liên quan + agent trả lời đúng (2), có liên quan nhưng thiếu/không ở top-1 (1), không có trong top-3 (0).

Kết quả dưới đây chạy bằng `gemini-embedding-001` (3.072 chiều, đã chuẩn hoá). Chi tiết đầy đủ trong `ket_qua_benchmark.txt`.

| # | Câu hỏi | Chiến lược tốt nhất cho câu này | Có chunk liên quan trong top-3? | Ghi chú |
|---|---------|-------------------------------|-------------------------------|---------|
| 1 | Bao nhiêu ngày để gửi yêu cầu trả hàng? | HeadingChunker | ✅ top-1, score 0,8037 | §3 trọn vẹn, chứa cả ngoại lệ 24 giờ cho thực phẩm tươi sống — 2/2 |
| 2 | Trạng thái nào hủy đơn được ngay? | HeadingChunker | ✅ top-1, score 0,8454 | Cả 3 slot đều từ đúng tài liệu; bảng trạng thái nằm trọn trong một chunk sau khi dựng lại Markdown — 2/2 |
| 3 | Thời hạn xử lý yêu cầu trả hàng? *(lọc seller)* | HeadingChunker **+ filter** | ✅ top-1, score 0,7458 | Không lọc thì **0/2**, có lọc **2/2** — chênh 2 điểm |
| 4 | Sản phẩm hoàn trả phải đáp ứng gì? | HeadingChunker | ✅ top-1, score 0,8310 | §6 là một đoạn liệt kê trọn vẹn, hợp với chunk theo heading — 2/2 |
| 5 | Hàng còn hạn sử dụng bao lâu? | HeadingChunker | ✅ top-1, score 0,8383 | §D tách riêng nên không bị §C (13 KB) nuốt — 2/2 |

**Tổng: 10/10.** Cùng bộ query và cùng chiến lược chunk nhưng chạy bằng `MockEmbedder` thì ra **0/10** — xem so sánh trong `REPORT_CANHAN` mục 5.

**Lọc bằng metadata có giúp ích không? Ở câu hỏi nào?**
> **Có, ở câu 3, và đo được chênh lệch 2 điểm.** Chạy A/B trên đúng câu đó:
>
> | Lần chạy | Top-3 | Điểm |
> |---|---|---|
> | Không lọc | `[buyer]`return-refund-buyer#6 (§3, "15 ngày") · `[seller]`return-refund-seller#0 · `[buyer]`return-refund-buyer#0 | **0/2** — gold ở top-2 nhưng ngữ cảnh không chứa "02 ngày lịch" |
> | Lọc `audience=seller` | `[seller]`return-refund-seller#0 · #1 (§5) · #4 (§7) | **2/2** — gold top-1, ngữ cảnh chứa đáp án |
>
> Không lọc thì top-1 là điều khoản của **người mua** với con số 15 ngày. Agent sẽ trả lời trôi chảy nhưng **sai đối tượng** — kiểu lỗi nguy hiểm vì nhìn vào câu trả lời không thấy dấu hiệu bất thường nào. Đây là lý do việc tách `shopee-return-refund-policy` thành hai file theo `audience` (mục 1) không phải là làm cho đẹp schema mà là điều kiện để filter có tác dụng.
>
> **Mặt trái:** filter dùng so sánh `==` nên lọc `seller` sẽ loại luôn tài liệu gắn `both` (`shipping-policy`) dù nó áp dụng cho cả hai bên. Với 5 câu hiện tại chưa gây hại, nhưng một câu hỏi về khiếu nại vận chuyển của người bán sẽ mất đúng tài liệu cần. Đây là đánh đổi precision/recall, cách sửa là cho filter chấp nhận `audience in (giá trị, "both")` thay vì bằng tuyệt đối.

---

## 4. Thuyết trình (Demo) & Bài học nhóm — Nhóm (5 điểm)

**Những phân tích (insights) hay nhất nhóm sẽ trình bày:**
> 1. **Chấm theo `doc_id` thổi phồng kết quả.** Cùng một lượt chạy, chấm ngây thơ ra 2/10 còn chấm ở mức nội dung ra 0/10 — vì câu 1 và câu 5 có gold `doc_id` ở top-2 nhưng lọt vào **sai section**, ngữ cảnh không chứa con số cần trả lời.
> 2. **Metadata schema đẹp trên giấy vẫn có thể vô dụng khi chạy.** Trang chính sách trả hàng gốc gộp cả thời hạn người mua (15 ngày) lẫn thời hạn người bán (02 ngày lịch); để nguyên một file `audience: both` thì filter không có gì để lọc. Phải tách đôi tài liệu thì filter mới có việc thật.
> 3. **Crawler của repo tự làm hỏng filter.** Hàm `yaml_value()` bọc mọi giá trị front matter bằng ngoặc kép, nên `metadata['audience']` đọc ra là `'"seller"'` — `metadata_filter={"audience": "seller"}` không khớp gì và `search_with_filter()` luôn trả rỗng. Lỗi này im lặng cho tới tận lúc benchmark.
> 4. **Backend embedding quyết định tất cả.** Cùng corpus, cùng chiến lược chunk, cùng bộ query: `MockEmbedder` ra **0/10**, `gemini-embedding-001` ra **10/10**. Mock chỉ đủ để kiểm pipeline có chạy không.
> 5. **A/B không đổi kết quả nghĩa là câu hỏi sai, không phải filter vô dụng.** Câu 3 bản đầu nêu thẳng "bên bán" nên embedder tự tìm đúng, hai lần chạy giống hệt nhau. Sửa câu hỏi cho mơ hồ về đối tượng thì mới đo được chênh lệch 2 điểm.
> 6. **Benchmark bão hoà thì điểm số mất khả năng phân biệt.** Cả 4 chiến lược đều 10/10, nhưng tỉ lệ chunk bị cắt giữa câu chênh từ 0% đến 83%. Khi mọi chiến lược đều đạt điểm tối đa, phải đổi sang chỉ số khác (độ mạch lạc, phân bố kích thước) hoặc viết query khó hơn — chứ không kết luận "chọn gì cũng như nhau".

### Phân tích lỗi (Failure Analysis)

**Failure case 1 — chunk chỉ chứa tiêu đề thắng top-1 dù không có đáp án nào**

- *Câu hỏi nào hỏng:* Q2, Q3, Q4 đều có top-1 là một chunk **chỉ gồm đúng dòng tiêu đề tài liệu**: `buyer-cancel-order#0` = `"# Quy định hủy đơn hàng dành cho Người Mua"` (42 ký tự), `return-refund-seller#0` = `"# Chính sách Trả hàng và Hoàn tiền — trách nhiệm Người Bán"` (58 ký tự). Cả ba câu vẫn được 2/2 nhưng **nhờ chunk xếp thứ 2 và 3**, không phải nhờ top-1.
- *Tại sao:* cosine đo **độ giống chủ đề**, không đo mật độ thông tin trả lời được. Một dòng tiêu đề là bản tóm tắt chủ đề cô đặc nhất có thể nên luôn khớp cao với câu hỏi cùng chủ đề — trong khi nó chứa đúng 0 dữ kiện. Đo được: **10/157 chunk dưới 120 ký tự**, phần lớn là tiêu đề hoặc mục một câu.
- *Đề xuất sửa:* gom chunk dưới ngưỡng tối thiểu (khoảng 200 ký tự) vào mục kế tiếp, đúng bước "gom lên" mà `RecursiveChunker` đã làm nhưng `HeadingChunker` hiện chưa. Nếu `top_k=1` thì lỗi này đã thành 0 điểm ở cả ba câu — hiện chỉ thoát nhờ `top_k=3`.

**Failure case 2 — không lọc `audience` thì agent trả lời sai đối tượng (Q3)**

- *Câu hỏi nào hỏng:* Q3 "Thời hạn xử lý một yêu cầu trả hàng là bao nhiêu ngày?" khi chạy **không** filter — top-1 là `return-refund-buyer#6` (§3, "15 ngày"), tức điều khoản của **người mua**, trong khi câu hỏi (ngầm) hỏi về người bán. Điểm 0/2.
- *Tại sao:* hai tài liệu cùng chủ đề, cùng từ vựng pháp lý, chỉ khác đối tượng áp dụng. Embedding không phân biệt được đối tượng vì câu hỏi không nêu — đó là thông tin nằm ở **metadata**, không nằm ở text.
- *Đề xuất sửa:* đúng cách đang dùng — tách tài liệu theo `audience` rồi lọc trước khi search, chênh 2 điểm. Nguy hiểm của lỗi này là agent vẫn trả lời trôi chảy và có trích dẫn, chỉ sai đối tượng, nên **không thể phát hiện bằng cách đọc câu trả lời** — phải đối chiếu `doc_id` của chunk được dùng.

**Failure case 3 — bộ benchmark bão hoà, không phân biệt được chiến lược**

- *Câu hỏi nào hỏng:* cả 5, theo nghĩa khác — chúng **quá dễ**. Chạy cả 4 chiến lược trên cùng corpus, cùng backend: `fixed_size` 10/10, `by_sentences` 10/10, `recursive` 10/10, `HeadingChunker` 10/10. Bộ đo không nói được chiến lược nào tốt hơn.
- *Tại sao:* mỗi câu hỏi nhắm vào một điều khoản duy nhất, dùng từ khoá gần như trùng với văn bản gốc ("hạn sử dụng", "hoàn trả", "hủy đơn"). Với embedder thật thì chunk chứa đáp án luôn thắng, bất kể ranh giới cắt ở đâu. Chỉ khi chạy bằng `MockEmbedder` bộ query mới phân biệt được — mà lúc đó nó phân biệt bằng nhiễu.
- *Đề xuất sửa:* (a) thêm câu hỏi cần **tổng hợp từ hai mục khác nhau** trong cùng tài liệu, hoặc từ hai tài liệu — chiến lược cắt vụn sẽ lộ ngay; (b) thêm câu hỏi dùng từ ngữ **không trùng** với văn bản gốc, buộc embedding phải bắc cầu ngữ nghĩa; (c) hạ `top_k` từ 3 xuống 1 — làm vậy `HeadingChunker` mất 6/10 vì chunk tiêu đề rỗng chiếm top-1, còn `recursive` giữ nguyên, và thứ hạng giữa các chiến lược hiện ra ngay.

**Failure case 4 — chấm theo `doc_id` tự đánh lừa mình (lượt chạy mock)**

- *Câu hỏi nào hỏng:* Q1 và Q5 ở lượt chạy `MockEmbedder`.
- *Tại sao:* gold `doc_id` nằm trong top-3 nên chấm ngây thơ cho 1 điểm mỗi câu (tổng 2/10), nhưng chunk lọt vào là **sai section** — `return-refund-buyer#1` (§1 Đối tượng áp dụng) thay vì §3.2 chứa "15 (mười lăm) ngày". Chấm ở mức nội dung ra 0/10.
- *Đề xuất sửa:* khai báo cho mỗi câu một chuỗi đặc trưng bắt buộc phải xuất hiện trong ngữ cảnh truy xuất được, rồi kiểm chuỗi đó — đúng cách `bench.py` đang làm qua trường `must_contain`. Thêm bằng chứng cho thấy mock hoàn toàn là nhiễu: `voucher-refund-policy#11` (§14 Từ chối mã ưu đãi giả mạo) đứng top-1 cho **cả Q4 lẫn Q5**, hai câu chẳng liên quan gì tới mã ưu đãi. Một chunk thắng mọi truy vấn là dấu hiệu của hàm băm, không phải của ngữ nghĩa.

**Bài học rút ra khi so sánh trong nhóm:**
> **Bài học lớn nhất lại không nằm ở chunking mà ở quy trình: nhóm quên chốt biến số trước khi đo.** Câu hỏi của lab là "cùng tài liệu nhưng chiến lược khác nhau dẫn tới khác biệt gì" — nhóm không trả lời được, vì đã vô tình đổi *bốn* biến cùng lúc (corpus, bộ query, backend, chiến lược) nên không quy được khác biệt về nguyên nhân nào. Một thành viên đạt 10/10, một đạt 5/5, một đạt 1/5, nhưng ba con số đó đo ba thứ khác nhau.
>
> Khi dựng lại phép đo **có kiểm soát** (mục 3b) thì bài học thật mới hiện ra, và nó ngược với trực giác ban đầu: **chiến lược chunking gần như không ảnh hưởng tới điểm** — cả bốn đều 10/10 — trong khi **backend embedding quyết định tất cả** (0/10 với mock, 10/10 với Gemini, cùng chiến lược cùng corpus). Nhóm đã dành phần lớn thời gian tranh luận về chunking, thứ hoá ra ít quan trọng nhất trong ba biến.
>
> Khác biệt thật giữa các chiến lược chỉ lộ ra ở chỉ số **không phải điểm số**: tỉ lệ chunk bị cắt giữa câu, từ 83% (`fixed_size`) xuống 0% (`HeadingChunker`). Cùng được 2/2 ở một câu, nhưng một bên trả về mảnh bắt đầu bằng `"thuận này)."` còn bên kia trả về nguyên điều khoản kèm tiêu đề.

**Nếu làm lại, nhóm sẽ thay đổi gì trong chiến lược dữ liệu (data strategy)?**
> **1. Đóng băng corpus và bộ query trước khi ai đó bắt đầu đo.** Chốt một commit làm mốc, tất cả chạy trên đúng commit đó. Sai lầm cụ thể lần này: corpus bị lọc bớt 6 tài liệu *sau khi* một thành viên đã chạy benchmark, nên kết quả của bạn ấy trỏ vào hai file không còn tồn tại.
>
> **2. Thống nhất backend trước, vì nó át mọi biến khác.** Một Gemini API key miễn phí là đủ cho cả nhóm; nếu buộc phải dùng mock thì cả nhóm cùng dùng mock — quan trọng là giống nhau, không phải là tốt nhất.
>
> **3. Phân công chiến lược ngay từ đầu để không trùng.** Ba trên bốn người cùng chọn biến thể heading. Lần sau nên bốc thăm: một người `fixed_size` có overlap, một `recursive`, một `by_sentences`, một heading — đúng như vai R3 trong lab doc có nhiệm vụ bảo đảm.
>
> **4. Viết query khó hơn.** Bộ 5 câu hiện tại bão hoà — chiến lược nào cũng 10/10 nên không phân biệt được gì. Cần thêm câu buộc tổng hợp từ hai mục khác nhau, và câu dùng từ ngữ không trùng với văn bản gốc.
>
> **5. Về bản thân dữ liệu:** tách tài liệu theo `audience` là quyết định đúng và nên làm sớm hơn — nó là điều kiện để `metadata_filter` có tác dụng (đo được chênh 2 điểm ở câu 3). Ngược lại, để `audience: both` cho `shipping-policy` là thoả hiệp còn nợ: filter dùng `==` nên tài liệu `both` bị loại khỏi mọi truy vấn có lọc.

---

## Tự Đánh Giá (Phần Nhóm)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Lựa chọn tài liệu (Document Set Quality) | **9** / 10 | 7 tài liệu công khai, metadata đủ 7 trường, `sources.csv` khớp 1-1, `document_version` trích từ chính văn bản. Trừ điểm vì `shipping-policy` để `audience: both` khiến filter `==` loại nhầm nó |
| Thiết kế chiến lược (Strategy Design) | **12** / 15 | Có chiến lược custom + lý do + baseline 4 chiến lược + phép đo có kiểm soát. Trừ điểm vì so sánh giữa các thành viên không hợp lệ (lệch corpus/query/backend) và 3/4 người trùng chiến lược |
| Chất lượng truy xuất (Retrieval Quality) | **10** / 10 | 10/10 trên `gemini-embedding-001`, chấm hai mức, A/B chứng minh filter chênh 2 điểm |
| Thuyết trình (Demo) | **—** / 5 | Chưa thuyết trình; đã chuẩn bị 6 insight + 4 failure case và `bench.py` chạy sẵn |
| **Tổng phần nhóm** | **31–36** / 40 | tuỳ điểm demo |
