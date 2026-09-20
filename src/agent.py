from typing import Callable

from .store import EmbeddingStore


class KnowledgeBaseAgent:
    """
    An agent that answers questions using a vector knowledge base.

    Retrieval-augmented generation (RAG) pattern:
        1. Retrieve top-k relevant chunks from the store.
        2. Build a prompt with the chunks as context.
        3. Call the LLM to generate an answer.
    """

    NO_CONTEXT_MESSAGE = (
        "Không tìm thấy tài liệu liên quan trong cơ sở tri thức để trả lời câu hỏi này."
    )

    def __init__(self, store: EmbeddingStore, llm_fn: Callable[[str], str]) -> None:
        self.store = store
        self.llm_fn = llm_fn

    def _build_prompt(self, question: str, results: list[dict]) -> str:
        blocks = []
        for number, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            source = metadata.get("source_url") or metadata.get("source") or "không rõ"
            blocks.append(
                f"[{number}] (doc_id: {metadata.get('doc_id', result.get('id'))} "
                f"| nguồn: {source})\n{result['content']}"
            )
        context = "\n\n".join(blocks)

        return (
            "Bạn là trợ lý trả lời câu hỏi dựa trên tài liệu được cung cấp.\n\n"
            "QUY TẮC:\n"
            "- Chỉ dùng thông tin trong phần NGỮ CẢNH bên dưới. Không suy đoán, "
            "không dùng kiến thức ngoài.\n"
            "- Mỗi ý trong câu trả lời phải trích dẫn số hiệu đoạn đã dùng, ví dụ [1], [2].\n"
            "- Nếu ngữ cảnh không đủ để trả lời, hãy nói rõ là không tìm thấy thông tin "
            "thay vì đoán.\n\n"
            f"NGỮ CẢNH:\n{context}\n\n"
            f"CÂU HỎI: {question}\n\n"
            "TRẢ LỜI (kèm trích dẫn [số]):"
        )

    def answer(self, question: str, top_k: int = 3) -> str:
        # 1. Retrieve
        results = self.store.search(question, top_k=top_k)
        # Empty store or no hit: say so instead of burning an LLM call.
        if not results:
            return self.NO_CONTEXT_MESSAGE

        # 2. Build a numbered, source-tagged context so the answer stays traceable
        #    back to the exact chunk and file (Source Traceability, docs/EVALUATION.md).
        prompt = self._build_prompt(question, results)

        # 3. Generate
        return self.llm_fn(prompt)
