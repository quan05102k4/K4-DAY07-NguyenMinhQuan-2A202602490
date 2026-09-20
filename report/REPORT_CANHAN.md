# Báo Cáo Cá Nhân — Lab 7: Embedding & Vector Store

**Họ tên:** Nguyễn Minh Quân
**Nhóm:** fanboiPNV
**Ngày:** 20/09/2026

> **Nộp 1 bản / sinh viên.** Phần nhóm (lựa chọn tài liệu, thiết kế chiến lược, bộ câu hỏi đánh giá, demo) nộp chung 1 bản trong `REPORT_NHOM.md`. Chi tiết thang điểm: `docs/SCORING.md`.

**Tổng điểm phần cá nhân: 60** = Khởi động (5) + Hướng tiếp cận (10) + Hoàn thiện code (30) + Dự đoán độ tương tự (5) + Kết quả truy xuất của tôi (10).

---

## 1. Khởi động (Warm-up) — Cá nhân (5 điểm)

### Độ tương tự Cosine (Cosine Similarity) (Bài tập 1.1)

**Độ tương tự cosine cao (High cosine similarity) nghĩa là gì?**
> Cosine đo **góc** giữa hai vector, không đo độ dài của chúng. Similarity cao (gần 1) nghĩa là hai embedding chỉ gần như cùng một hướng trong không gian ngữ nghĩa, tức mô hình cho rằng hai đoạn text nói về cùng một điều — dù chúng dùng từ ngữ khác nhau và dài ngắn khác nhau.

**Ví dụ có độ tương tự CAO:**
- Câu A: "Người mua được trả hàng trong vòng 15 ngày kể từ khi nhận được đơn."
- Câu B: "Thời hạn yêu cầu hoàn trả sản phẩm là hai tuần tính từ lúc giao thành công."
- Tại sao tương đồng: Hai câu **gần như không dùng chung từ nào** — "trả hàng"/"hoàn trả sản phẩm", "15 ngày"/"hai tuần", "nhận được đơn"/"giao thành công" — nhưng diễn đạt đúng một quy định. Nếu embedding cho điểm cao ở cặp này thì nó đang hiểu **nghĩa**, chứ không phải đếm từ trùng nhau. Đây mới là phép thử thật; chọn hai câu chỉ khác một từ thì không chứng minh được gì vì so khớp từ khóa cũng làm được.

**Ví dụ có độ tương tự THẤP:**
- Câu A: "Người bán phải phản hồi yêu cầu trả hàng trong vòng 02 ngày lịch."
- Câu B: "Shopee cấm đăng bán động vật hoang dã và các chế phẩm từ động vật."
- Tại sao khác: Cùng lĩnh vực thương mại điện tử và cùng văn phong pháp lý, nhưng một câu nói về **thời hạn xử lý khiếu nại**, câu kia về **danh mục hàng cấm**. Không chung chủ đề nên hai vector trỏ về hai hướng khác nhau, điểm gần 0.

**Tại sao độ tương tự cosine (cosine similarity) được ưu tiên hơn khoảng cách Euclid (Euclidean distance) cho text embeddings?**
> Vì cosine **bỏ qua độ dài vector**, mà độ dài embedding lại phụ thuộc mạnh vào độ dài văn bản. Với khoảng cách Euclid, một điều khoản 3.000 ký tự và một câu 50 ký tự nói cùng một nội dung sẽ bị coi là "xa nhau" chỉ vì chênh lệch độ lớn; cosine vẫn nhận ra chúng cùng hướng. Trong lab này vector đã được chuẩn hoá (`||v|| = 1`) nên dot product bằng đúng cosine — đó là lý do docstring của `search` cho phép dùng dot product cho gọn.

### Bài toán tính toán Chunking (Bài tập 1.2)

**Tài liệu 10,000 ký tự, chunk_size=500, overlap=50. Bao nhiêu chunks?**
> **Phép tính:** mỗi chunk mới chỉ tiến thêm `step = chunk_size − overlap = 500 − 50 = 450` ký tự. Chunk đầu phủ 500 ký tự, mỗi chunk sau phủ thêm 450.
> `số chunk = ceil((10.000 − 50) / (500 − 50)) = ceil(9.950 / 450) = ceil(22,11) = 23`
>
> **Đáp án: 23 chunk.** Kiểm lại bằng chính code trong repo thay vì tin công thức suông:
>
> ```bash
> python -c "
> from src.chunking import FixedSizeChunker
> print(len(FixedSizeChunker(chunk_size=500, overlap=50).chunk('a'*10000)))
> "
> # 23
> ```
>
> Khớp. Chunk cuối chỉ dài 100 ký tự chứ không đủ 500 — phần dư của tài liệu.

**Nếu độ chồng chéo (overlap) tăng lên 100, số lượng chunk thay đổi thế nào? Tại sao muốn độ chồng chéo nhiều hơn?**
> Số chunk **tăng lên 25**: `ceil((10.000 − 100) / (500 − 100)) = ceil(24,75) = 25` — đã chạy lại `FixedSizeChunker(chunk_size=500, overlap=100)` và ra đúng 25. Overlap lớn hơn nghĩa là bước tiến nhỏ hơn nên cần nhiều chunk hơn để phủ hết tài liệu, tốn thêm chi phí embedding và lưu trữ.
>
> Vẫn muốn overlap lớn khi **thông tin cần trả lời nằm vắt qua ranh giới chunk**. Cắt cứng theo kích thước có thể chia đôi một câu chứa con số quan trọng — ví dụ "Người Mua có thể gửi yêu cầu trả hàng trong vòng 15 (mười lăm) ngày" bị cắt giữa "15" và "ngày" thì không chunk nào trả lời được câu hỏi về thời hạn. Overlap cho mỗi thông tin **nhiều hơn một cơ hội** lọt vào top-k. Đây chính là đánh đổi: trả thêm chunk để đổi lấy recall.

---

## 2. Hướng tiếp cận của tôi (My Approach) — Cá nhân (10 điểm)

Giải thích cách tiếp cận của bạn khi lập trình (implement) các phần chính trong gói `src`.

### Các hàm chia nhỏ (Chunking Functions)

**`SentenceChunker.chunk`** — hướng tiếp cận:
> Dùng `re.split(r"(?<=[.!?])\s+", text)`. Điểm mấu chốt là **lookbehind** `(?<=...)`: nó kiểm tra dấu câu nhưng **không tiêu thụ** ký tự đó, nên chỗ cắt nằm ở khoảng trắng *sau* dấu chấm và dấu câu vẫn dính lại với câu của nó. Nếu split bằng `[.!?]\s+` thì dấu câu bị nuốt mất và mọi chunk thành câu cụt. Một regex này phủ luôn cả bốn trường hợp đề bài nêu (`". "`, `"! "`, `"? "`, `".\n"`) vì `\s+` khớp cả dấu cách lẫn xuống dòng. Text rỗng hoặc chỉ có khoảng trắng trả `[]`, không crash.
>
> **Edge case tôi biết là chưa xử lý được** (đã chạy thử để kiểm chứng chứ không phỏng đoán):
>
> | Đầu vào | Kết quả | Đánh giá |
> |---|---|---|
> | `TS. Nguyễn Văn A đã công bố.` | `['TS.', 'Nguyễn Văn A đã công bố.']` | ❌ Sai — viết tắt bị coi là hết câu |
> | `3.2. Người Mua có thể gửi yêu cầu…` | `['3.2.', 'Người Mua có thể gửi yêu cầu…']` | ❌ Sai — **nghiêm trọng nhất với corpus của tôi** |
> | `a. Hàng hóa thuộc danh mục cấm.` | `['a.', 'Hàng hóa thuộc danh mục cấm.']` | ❌ Sai |
> | `Phí là 2.5 phần trăm.` | `['Phí là 2.5 phần trăm.']` | ✅ Đúng — không có khoảng trắng sau dấu chấm nên không cắt |
>
> Hai điều đáng nói. Thứ nhất, **số thập phân thực ra an toàn**, khác với dự đoán thông thường: `2.5` không có khoảng trắng sau dấu chấm nên `\s+` không khớp. Thứ hai, thứ thật sự nguy hiểm với corpus của tôi lại là **số hiệu điều khoản** — toàn bộ tài liệu chính sách Shopee đánh số theo dạng `3.2.`, `a.`, `I.`, nên `SentenceChunker` sẽ tách số hiệu thành chunk mồ côi 3–4 ký tự, vừa vô nghĩa khi truy xuất vừa làm câu ngay sau đó mất ngữ cảnh "đây là điều khoản mấy". Cách sửa nếu có thêm thời gian: thêm điều kiện lookbehind loại trừ các token ngắn kết thúc bằng dấu chấm, hoặc dùng thư viện tách câu chuyên dụng thay vì regex tự viết.

**`RecursiveChunker.chunk` / `_split`** — hướng tiếp cận:
> Thuật toán chạy **hai chiều**, và đây là chỗ dễ chỉ viết một nửa. *Xuống sâu*: thử separator theo thứ tự ưu tiên `["\n\n", "\n", ". ", " ", ""]`, cắt bằng ranh giới "to" trước để giữ ngữ nghĩa; mảnh nào vẫn dài hơn `chunk_size` thì gọi lại `_split` với danh sách separator còn lại. *Gom lên*: sau khi cắt, các mảnh nhỏ liền kề được nối lại (kèm separator) cho tới sát `chunk_size`. Thiếu bước gom thì một file nhiều dòng ngắn sinh ra hàng trăm chunk vụn 5–10 ký tự và retrieval sẽ rất tệ.
>
> **Ba base case:**
> 1. `current_text` rỗng → trả `[]`.
> 2. `len(current_text) <= chunk_size` → đã đủ nhỏ, trả `[current_text]`, không cắt nữa.
> 3. Hết separator (`remaining_separators == []`) **hoặc** separator hiện tại là chuỗi rỗng `""` → không còn ranh giới ngữ nghĩa nào để dựa vào, cắt cứng theo `chunk_size`.
>
> Nhánh thứ 3 chính là chỗ test `test_empty_separators_falls_back_gracefully` nhắm tới — nó truyền thẳng `separators=[]`, thiếu nhánh này là fail hoặc lặp vô hạn.

### Lớp EmbeddingStore

> **Quyết định đầu tiên: bỏ hẳn nhánh ChromaDB, chỉ dùng in-memory.** Code khởi tạo sẵn có một cái bẫy — `self._use_chroma = True` được gán *trước* khi client được tạo. Không test nào cần Chroma và `requirements.txt` không cài nó, nhưng nếu máy chấm bài tình cờ có `chromadb` thì mọi method sẽ rẽ vào nhánh chưa cài đặt và cả 14 test sập. Tôi để `_use_chroma = False` cứng và ghi chú lý do ngay tại chỗ.
>
> **Viết hai helper trước, bốn method công khai sau** — làm ngược lại sẽ lặp cùng một logic bốn lần.

**`add_documents` + `search`** — hướng tiếp cận:
> `_make_record` chuẩn hoá một `Document` thành record. Hai chi tiết đáng nghĩ: (1) **copy** `doc.metadata` bằng `dict(...)` thay vì giữ tham chiếu tới object của người gọi — nếu họ sửa dict sau đó thì dữ liệu đã lưu bị hỏng âm thầm; (2) `metadata.setdefault("doc_id", doc.id)` để record **luôn** có khoá `doc_id`, vì `delete_document` phụ thuộc vào nó. Ở `bench.py` một file sinh ra nhiều `Document` với id `"file#0"`, `"file#1"`, nên `doc_id` phải trỏ về **file gốc** chứ không phải id của chunk.
>
> `add_documents` chỉ append — **một `Document` = một record, store không tự chunk**. Chunking nằm ở tầng ngoài (`bench.py`). Đây là lý do test đưa vào 3 `Document` và mong `get_collection_size() == 3`.
>
> `search` uỷ quyền hoàn toàn cho `_search_records(query, self._store, top_k)`. Độ tương tự dùng `_dot` vì vector đã chuẩn hoá (`||v|| = 1`) nên dot product **bằng đúng** cosine — đúng như docstring cho phép. Sắp xếp giảm dần theo score, dùng `index` (thứ tự nạp) để phá hoà nên kết quả tái lập được. Record trả về **bỏ trường `embedding`** — vector 1536 chiều làm bẩn output khi in ra terminal.

**`search_with_filter` + `delete_document`** — hướng tiếp cận:
> **Lọc TRƯỚC rồi mới search.** Nếu lấy top-k trước rồi mới bỏ cái không khớp, bạn có thể còn lại 0 kết quả dù store vẫn còn tài liệu hợp lệ — k slot đã bị chiếm hết bởi tài liệu sai đối tượng. Với corpus của tôi điều này rất dễ xảy ra: `return-refund-buyer` và `return-refund-seller` cùng chủ đề, cùng từ vựng, nên tài liệu buyer hoàn toàn có thể chiếm cả 3 slot của một câu hỏi về người bán.
>
> Cả `search()` và `search_with_filter()` đều đi qua **cùng một** `_search_records`, chỉ khác tập ứng viên đầu vào. Nhờ vậy hai đường không thể lệch kết quả và test `test_no_filter_returns_all_candidates` pass hiển nhiên chứ không phải nhờ may.
>
> `delete_document` lọc lại list, giữ những record có `metadata['doc_id'] != doc_id`, rồi so sánh độ dài trước/sau để trả `True`/`False`. Xoá theo `doc_id` nên một lệnh gỡ sạch **mọi chunk** của cùng một file.

### Tác tử KnowledgeBaseAgent

**`answer`** — hướng tiếp cận:
> Ba nhịp: truy xuất top-k → dựng prompt có ngữ cảnh → gọi `llm_fn`.
>
> Phần đáng đầu tư là **cách dựng ngữ cảnh**. Tôi đánh số từng chunk `[1] [2] [3]` kèm `doc_id` và `source_url`, rồi yêu cầu model trích dẫn số đó khi trả lời. Nhờ vậy câu trả lời **truy vết được** về đúng chunk và đúng file — đây là tiêu chí *Source Traceability* trong `docs/EVALUATION.md`, và với corpus là văn bản quy định thì nó không phải tính năng phụ: người đọc phải kiểm được câu trả lời dựa trên điều khoản nào.
>
> Hai ràng buộc chống bịa trong prompt: chỉ dùng thông tin trong phần NGỮ CẢNH, và nếu không đủ dữ kiện thì **nói rõ là không tìm thấy** thay vì đoán. Trường hợp store rỗng hoặc không có kết quả thì trả thẳng `NO_CONTEXT_MESSAGE` — không crash và không gọi LLM vô ích.

---

## 3. Hoàn thiện code (Core Implementation) — Cá nhân (30 điểm)

Vượt qua bộ kiểm thử là điều kiện tính điểm phần này.

### Kết Quả Kiểm Thử (Test Results)

```
$ pytest tests/ -v

============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0 -- F:\AI_lab\K4-DAY07-NguyenMinhQuan-2A202602490\.venv\Scripts\python.exe
cachedir: .pytest_cache
rootdir: F:\AI_lab\K4-DAY07-NguyenMinhQuan-2A202602490
collecting ... collected 42 items

tests/test_solution.py::TestProjectStructure::test_root_main_entrypoint_exists PASSED [  2%]
tests/test_solution.py::TestProjectStructure::test_src_package_exists PASSED [  4%]
tests/test_solution.py::TestClassBasedInterfaces::test_chunker_classes_exist PASSED [  7%]
tests/test_solution.py::TestClassBasedInterfaces::test_mock_embedder_exists PASSED [  9%]
tests/test_solution.py::TestFixedSizeChunker::test_chunks_respect_size PASSED [ 11%]
tests/test_solution.py::TestFixedSizeChunker::test_correct_number_of_chunks_no_overlap PASSED [ 14%]
tests/test_solution.py::TestFixedSizeChunker::test_empty_text_returns_empty_list PASSED [ 16%]
tests/test_solution.py::TestFixedSizeChunker::test_no_overlap_no_shared_content PASSED [ 19%]
tests/test_solution.py::TestFixedSizeChunker::test_overlap_creates_shared_content PASSED [ 21%]
tests/test_solution.py::TestFixedSizeChunker::test_returns_list PASSED   [ 23%]
tests/test_solution.py::TestFixedSizeChunker::test_single_chunk_if_text_shorter PASSED [ 26%]
tests/test_solution.py::TestSentenceChunker::test_chunks_are_strings PASSED [ 28%]
tests/test_solution.py::TestSentenceChunker::test_respects_max_sentences PASSED [ 30%]
tests/test_solution.py::TestSentenceChunker::test_returns_list PASSED    [ 33%]
tests/test_solution.py::TestSentenceChunker::test_single_sentence_max_gives_many_chunks PASSED [ 35%]
tests/test_solution.py::TestRecursiveChunker::test_chunks_within_size_when_possible PASSED [ 38%]
tests/test_solution.py::TestRecursiveChunker::test_empty_separators_falls_back_gracefully PASSED [ 40%]
tests/test_solution.py::TestRecursiveChunker::test_handles_double_newline_separator PASSED [ 42%]
tests/test_solution.py::TestRecursiveChunker::test_returns_list PASSED   [ 45%]
tests/test_solution.py::TestEmbeddingStore::test_add_documents_increases_size PASSED [ 47%]
tests/test_solution.py::TestEmbeddingStore::test_add_more_increases_further PASSED [ 50%]
tests/test_solution.py::TestEmbeddingStore::test_initial_size_is_zero PASSED [ 52%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_content_key PASSED [ 54%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_have_score_key PASSED [ 57%]
tests/test_solution.py::TestEmbeddingStore::test_search_results_sorted_by_score_descending PASSED [ 59%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_at_most_top_k PASSED [ 61%]
tests/test_solution.py::TestEmbeddingStore::test_search_returns_list PASSED [ 64%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_non_empty PASSED [ 66%]
tests/test_solution.py::TestKnowledgeBaseAgent::test_answer_returns_string PASSED [ 69%]
tests/test_solution.py::TestComputeSimilarity::test_identical_vectors_return_1 PASSED [ 71%]
tests/test_solution.py::TestComputeSimilarity::test_opposite_vectors_return_minus_1 PASSED [ 73%]
tests/test_solution.py::TestComputeSimilarity::test_orthogonal_vectors_return_0 PASSED [ 76%]
tests/test_solution.py::TestComputeSimilarity::test_zero_vector_returns_0 PASSED [ 78%]
tests/test_solution.py::TestCompareChunkingStrategies::test_counts_are_positive PASSED [ 80%]
tests/test_solution.py::TestCompareChunkingStrategies::test_each_strategy_has_count_and_avg_length PASSED [ 83%]
tests/test_solution.py::TestCompareChunkingStrategies::test_returns_three_strategies PASSED [ 85%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_filter_by_department PASSED [ 88%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_no_filter_returns_all_candidates PASSED [ 90%]
tests/test_solution.py::TestEmbeddingStoreSearchWithFilter::test_returns_at_most_top_k PASSED [ 92%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_reduces_collection_size PASSED [ 95%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_false_for_nonexistent_doc PASSED [ 97%]
tests/test_solution.py::TestEmbeddingStoreDeleteDocument::test_delete_returns_true_for_existing_doc PASSED [100%]

============================= 42 passed in 0.12s ==============================
```

**Số lượng bài test vượt qua (pass):** **42** / 42

Không còn `raise NotImplementedError` nào trong `src/` — đã kiểm bằng `grep -rn "NotImplementedError" src/`, không ra kết quả.

---

## 4. Dự đoán độ tương tự (Similarity Predictions) — Cá nhân (5 điểm)

Năm cặp câu lấy từ chủ đề của corpus, mỗi cặp thử một tính chất khác nhau của embedding. Chạy bằng `gemini-embedding-001` qua `compute_similarity()`.

| Cặp | Câu A | Câu B | Phép thử | Dự đoán | Điểm thực tế | Đúng? |
|------|-----------|-----------|---------|---------|--------------|-------|
| 1 | Người mua được trả hàng trong vòng 15 ngày kể từ khi nhận được đơn. | Thời hạn yêu cầu hoàn trả sản phẩm là hai tuần tính từ lúc giao thành công. | Khác từ vựng, cùng nghĩa | cao | **0,7754** | ✅ Đúng |
| 2 | Người mua có 15 ngày để gửi yêu cầu trả hàng. | Người bán có 02 ngày lịch để phản hồi yêu cầu trả hàng. | Trùng nhiều từ, khác đối tượng và khác đáp án | cao | **0,8570** | ✅ Đúng |
| 3 | Sản phẩm hoàn trả phải còn nguyên vẹn và đủ phụ kiện. | Shopee cấm đăng bán động vật hoang dã và chế phẩm từ động vật. | Khác hẳn chủ đề | thấp | **0,5931** | ✅ Đúng |
| 4 | Đơn hàng ở trạng thái Chờ xác nhận thì hủy được ngay. | Khi đơn chưa được người bán xác nhận, người mua có thể tự hủy mà không cần chờ duyệt. | Cùng nghĩa, diễn đạt dài ngắn khác nhau | cao | **0,8987** | ✅ Đúng |
| 5 | Hàng hóa phải còn ít nhất 30% hạn sử dụng khi giao đi. | Người bán chịu chi phí vận chuyển chiều hoàn trả nếu giao không thành công. | Cùng vai (người bán), khác nghĩa vụ | thấp | **0,6885** | ✅ Đúng |

**Xếp hạng thực tế, cao xuống thấp:** cặp 4 (0,8987) › cặp 2 (0,8570) › cặp 1 (0,7754) › cặp 5 (0,6885) › cặp 3 (0,5931).

Đúng 5/5 dự đoán ở mức cao/thấp. Nhưng **thứ hạng** mới là chỗ đáng nói.

**Kết quả nào bất ngờ nhất? Điều này nói gì về cách embeddings biểu diễn ý nghĩa?**
> **Cặp 2 (0,8570) được chấm CAO HƠN cặp 1 (0,7754)** — dù cặp 1 là hai câu *cùng một nghĩa*, còn cặp 2 là hai câu *khác đối tượng và khác đáp án* (15 ngày của người mua vs 02 ngày lịch của người bán). Embedding xếp "trùng bề mặt" lên trên "tương đương ngữ nghĩa": cặp 2 dùng chung sẵn các từ "người", "ngày", "yêu cầu trả hàng" nên được điểm cao dễ dàng, trong khi cặp 1 phải tự bắc cầu "15 ngày"↔"hai tuần" và "trả hàng"↔"hoàn trả sản phẩm" — nó làm được thật (0,775 là cao), nhưng vẫn thua độ trùng từ thô.
>
> Đây chính là lời giải thích bằng số cho việc **vì sao phải dùng `metadata_filter`**. Cặp 2 đúng là hai tài liệu `return-refund-buyer` và `return-refund-seller` trong corpus. Với similarity 0,857, retrieval **không thể phân biệt hai tài liệu đó bằng embedding** — thông tin "câu này dành cho ai" không nằm trong text mà nằm ở metadata. Không lọc thì Q3 lấy nhầm điều khoản của người mua, đúng như A/B ở mục 5 đo được.
>
> Điều bất ngờ thứ hai: **cặp 3 không hề gần 0 mà là 0,5931**, dù hai câu chẳng liên quan gì nhau (sản phẩm hoàn trả vs cấm bán động vật hoang dã). Với `gemini-embedding-001`, hai câu tiếng Việt cùng văn phong pháp lý thương mại điện tử đã có "sàn" tương đồng quanh 0,6. Hệ quả thực tế: **không thể đặt ngưỡng tuyệt đối** kiểu "score > 0,5 là liên quan" để lọc nhiễu — 0,59 ở đây là *không liên quan*, trong khi ở thang khác lại là cao. Chỉ có thứ hạng tương đối trong cùng một truy vấn mới đáng tin.

---

## 5. Kết quả truy xuất của tôi (Competition Results) — Cá nhân (10 điểm)

Chạy **5 câu hỏi đánh giá của nhóm** trên mã nguồn cá nhân của bạn trong gói `src`. **5 câu hỏi này phải trùng với các thành viên cùng nhóm** (xem `REPORT_NHOM.md`).

**Chiến lược của tôi:** `HeadingChunker(chunk_size=800)` — chia theo tiêu đề/mục của điều khoản, mục nào dài quá ngưỡng thì hạ xuống `RecursiveChunker` và gắn lại tiêu đề vào từng mảnh con. Nạp **157 chunk** từ 7 file (dài min 34 / trung bình 596 / max 867 ký tự). Kết quả đầy đủ trong `ket_qua_benchmark.txt`, sinh bằng `python bench.py -o ket_qua_benchmark.txt`.

**Embedding backend:** `gemini-embedding-001` (3.072 chiều, đã chuẩn hoá `||v|| = 1` nên dot product bằng đúng cosine). `bench.py` cache embedding theo hash nội dung nên chạy lại không tốn thêm lượt gọi API.

| # | Câu hỏi (Query) | Top-1 Chunk truy xuất được (tóm tắt) | Điểm Score | Có liên quan không? (Relevant) | Câu trả lời của Agent (tóm tắt) |
|---|-------|--------------------------------|-------|-----------|------------------------|
| 1 | Người mua có bao nhiêu ngày để gửi yêu cầu trả hàng? | `return-refund-buyer#6` — §3 Điều kiện yêu cầu trả hàng/hoàn tiền | +0,8037 | ✅ Có, chứa "15 (mười lăm) ngày" | 15 ngày; thực phẩm tươi sống/đông lạnh 24 giờ [1] |
| 2 | Trạng thái nào hủy đơn được ngay? | `buyer-cancel-order#0` — tiêu đề tài liệu | +0,8454 | ✅ Có, top-2 và top-3 chứa bảng trạng thái | Chờ xác nhận hủy ngay; Chờ lấy hàng phải chờ người bán [2][3] |
| 3 | Thời hạn xử lý một yêu cầu trả hàng là bao nhiêu ngày? *(lọc `audience=seller`)* | `return-refund-seller#0` — tiêu đề tài liệu | +0,7458 | ✅ Có, top-2 là §5 chứa "02 ngày lịch" | 02 ngày lịch kể từ ngày nhận thông báo [2] |
| 4 | Sản phẩm hoàn trả phải đáp ứng gì? | `return-refund-buyer#16` — §6 Yêu cầu đối với sản phẩm hoàn trả | +0,8310 | ✅ Có, chứa "hóa đơn thuế GTGT" | Nguyên vẹn, đủ phụ kiện, hóa đơn GTGT, tem bảo hành, quay video [1] |
| 5 | Hàng phải còn hạn sử dụng bao lâu? | `seller-listing-rules#27` — §D Quy định về hạn sử dụng | +0,8383 | ✅ Có, chứa "ít nhất 30%" | Còn ít nhất 30% hạn sử dụng và ít nhất 30 ngày [1] |

**Bao nhiêu câu hỏi trả về chunk có liên quan trong top-3?** **5** / 5. Tổng **10/10 điểm** (chấm ở mức nội dung).

### So sánh trực tiếp: MockEmbedder vs embedder thật

Tôi chạy đúng cùng bộ query, cùng chiến lược chunk, chỉ đổi backend:

| Backend | Tổng điểm | Ví dụ điển hình |
|---|---|---|
| `MockEmbedder` (băm MD5) | **0/10** | `voucher-refund-policy#11` (§14 Từ chối mã ưu đãi giả mạo) đứng **top-1 cho cả Q4 lẫn Q5** — hai câu chẳng liên quan gì tới mã ưu đãi |
| `gemini-embedding-001` | **10/10** | Mọi câu đều có gold ở top-1, score 0,74–0,85 |

Một chunk thắng mọi truy vấn là dấu hiệu điển hình của hàm băm chứ không phải của ngữ nghĩa. Điều này xác nhận cảnh báo của lab: benchmark bằng mock chỉ kiểm được pipeline có chạy không, **không nói gì về chất lượng truy xuất**.

### Phát hiện đáng giá nhất: hai cách chấm cho hai kết quả khác nhau

`bench.py` chấm ở **hai mức** thay vì một: (1) gold `doc_id` có trong top-3 không, (2) ngữ cảnh truy xuất được có thật sự chứa chuỗi đáp án không. Chênh lệch giữa hai cách lộ rõ nhất ở lượt chạy **mock**:

| # | Chấm ngây thơ (gold `doc_id` trong top-3?) | Chấm ở mức nội dung (ngữ cảnh chứa đáp án?) |
|---|---|---|
| 1 | ✅ top-2 → **1 điểm** | ❌ không chứa `"15 (mười lăm) ngày"` → **0 điểm** |
| 5 | ✅ top-2 → **1 điểm** | ❌ không chứa `"ít nhất 30%"` → **0 điểm** |

Chấm theo `doc_id` báo **2/10**, chấm ở mức nội dung báo **0/10**. Gold doc đúng nhưng lọt vào **sai section** — đúng thứ lab cảnh báo, và với `HeadingChunker` đặc biệt dễ xảy ra vì các section trong cùng tài liệu nói về cùng chủ đề nên điểm gần bằng nhau. Nếu chỉ chấm theo `doc_id` thì tôi đã tưởng mình được điểm ngay cả khi không chunk nào trả lời được.

### A/B bắt buộc — câu 3

Câu 3 **cố ý không nêu rõ ai hỏi** ("Thời hạn xử lý một yêu cầu trả hàng là bao nhiêu ngày?"), trong khi corpus có hai tài liệu cùng chủ đề, cùng từ vựng, khác đối tượng và khác đáp án — 15 ngày với người mua, 02 ngày lịch với người bán.

| Lần chạy | Top-3 | Kết quả |
|---|---|---|
| **Không** lọc | `[buyer]`return-refund-buyer#6 (§3, "15 ngày") · `[seller]`return-refund-seller#0 · `[buyer]`return-refund-buyer#0 | gold ở top-2 nhưng ngữ cảnh **không** chứa "02 ngày lịch" → **0/2** |
| **Có** `metadata_filter={"audience":"seller"}` | `[seller]`return-refund-seller#0 · #1 (§5) · #4 (§7) | gold top-1, ngữ cảnh chứa đáp án → **2/2** |

**Filter có tác dụng thật, chênh 2 điểm trên cùng một câu.** Không lọc thì top-1 là điều khoản của **người mua** với con số 15 ngày — agent sẽ trả lời trôi chảy nhưng **sai đối tượng**, đây là kiểu lỗi nguy hiểm vì nhìn vào câu trả lời không thấy có gì bất thường.
>
> **Ghi chú trung thực:** phiên bản đầu của câu 3 tôi viết là *"Sau khi nhận được thông báo về yêu cầu trả hàng, **bên bán** có bao lâu để gửi phản hồi?"* — nêu thẳng đối tượng. Chạy A/B thì hai lần cho kết quả **giống hệt nhau** (cả hai 2/2), tức câu hỏi chưa thực sự cần filter: embedder đã tự tìm đúng tài liệu nhờ từ "bên bán". Tôi sửa lại câu hỏi cho mơ hồ về đối tượng thì filter mới có việc thật. Đây chính là điều lab dặn — nếu A/B không đổi kết quả thì lỗi ở câu hỏi, không phải ở filter.

**Điều hay nhất tôi học được từ thành viên khác / nhóm khác (qua demo):**
> **Từ Đinh Bảo Hưng:** bạn giữ **toàn bộ đường dẫn heading** trong mỗi mảnh con, không chỉ heading gần nhất, với ngân sách `800 − độ dài đường dẫn − xuống dòng`. Lý do rất thuyết phục: trong corpus của bạn, mục "Stripe" xuất hiện ở cả hoàn tiền toàn bộ lẫn hoàn tiền một phần, chỉ đường dẫn mới phân biệt được. `HeadingChunker` của tôi chỉ gắn lại heading cấp gần nhất, nên với corpus Shopee có mục lồng ba cấp (`## D.` → `2.` → `a.`) thì mảnh con vẫn mơ hồ. Đây là cải tiến tôi sẽ lấy.
>
> **Từ Nguyễn Thành Nam:** bạn chạy `MarkdownHeadingChunker` trên `MockEmbedder` và chỉ được 1/5, nhưng thay vì giấu đi thì ghi rõ nguyên nhân là nhiễu hàm băm rồi **chuyển trọng tâm đánh giá sang độ mạch lạc của chunk**. Đúng cách lab dặn khi buộc phải dùng mock. Kết quả của bạn cũng là bằng chứng thứ hai, độc lập với tôi, rằng mock phá hỏng mọi số liệu ngữ nghĩa.
>
> **Bài học lớn nhất lại không phải về kỹ thuật.** Khi ghép bốn báo cáo lại mới thấy nhóm đã đổi *bốn* biến cùng lúc — corpus, bộ query, backend, chiến lược — nên ba con số 10/10, 5/5, 1/5 không so được với nhau. Tôi học được rằng **chốt biến số trước khi đo quan trọng hơn chọn chiến lược nào**: chính vì thấy điều đó mà tôi chạy lại phép đo có kiểm soát (4 chiến lược, cùng mọi điều kiện), và kết quả ngược hẳn trực giác — chiến lược gần như không ảnh hưởng điểm, backend mới quyết định tất cả.

---

## Tự Đánh Giá (Phần Cá Nhân)

| Tiêu chí | Điểm tự đánh giá | Căn cứ |
|----------|-------------------|--------|
| Khởi động (Warm-up) | **5** / 5 | Cosine giải thích kèm cặp câu khác từ vựng cùng nghĩa; bài toán chunking tính tay rồi kiểm lại bằng `FixedSizeChunker` thật (23 và 25 chunk) |
| Hướng tiếp cận của tôi (My Approach) | **10** / 10 | Đủ 3 phần, kèm bảng edge case của `SentenceChunker` đo thật và lý do bỏ nhánh ChromaDB |
| Hoàn thiện code (Core Implementation — tests) | **30** / 30 | `42 passed`, output thật đã dán ở mục 3, không còn `NotImplementedError` trong `src/` |
| Dự đoán độ tương tự (Similarity Predictions) | **5** / 5 | 5 cặp chạy bằng `gemini-embedding-001`, dự đoán ghi trước khi chạy, 5/5 đúng, phản ngẫm chỉ ra cặp 2 > cặp 1 và sàn 0,59 |
| Kết quả truy xuất của tôi (Competition Results) | **10** / 10 | 10/10 chấm ở mức nội dung, A/B chứng minh filter chênh 2 điểm, có ghi chú trung thực về việc phải sửa câu hỏi số 3 |
| **Tổng phần cá nhân** | **60** / 60 | |
