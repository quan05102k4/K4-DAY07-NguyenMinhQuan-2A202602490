from __future__ import annotations

from typing import Any, Callable

from .chunking import _dot
from .embeddings import _mock_embed
from .models import Document


class EmbeddingStore:
    """
    A vector store for text chunks.

    Tries to use ChromaDB if available; falls back to an in-memory store.
    The embedding_fn parameter allows injection of mock embeddings for tests.
    """

    def __init__(
        self,
        collection_name: str = "documents",
        embedding_fn: Callable[[str], list[float]] | None = None,
    ) -> None:
        self._embedding_fn = embedding_fn or _mock_embed
        self._collection_name = collection_name
        # In-memory only. The ChromaDB branch is deliberately not used: no test
        # needs it, requirements.txt does not install it, and flipping the flag
        # on a machine that happens to have chromadb would route every method
        # into an unimplemented path.
        self._use_chroma = False
        self._store: list[dict[str, Any]] = []
        self._collection = None
        self._next_index = 0

    def _make_record(self, doc: Document) -> dict[str, Any]:
        # Copy the caller's metadata: mutating their dict later would silently
        # corrupt what is already stored.
        metadata = dict(doc.metadata or {})
        # delete_document() matches on this key, so it must always exist. When a
        # file is chunked, Document.id looks like "file#0" while doc_id must keep
        # pointing at the source file.
        metadata.setdefault("doc_id", doc.id)

        record = {
            "index": self._next_index,
            "id": doc.id,
            "content": doc.content,
            "metadata": metadata,
            "embedding": self._embedding_fn(doc.content),
        }
        self._next_index += 1
        return record

    def _search_records(self, query: str, records: list[dict[str, Any]], top_k: int) -> list[dict[str, Any]]:
        if not records or top_k <= 0:
            return []

        query_embedding = self._embedding_fn(query)
        # Embeddings are normalised (||v|| = 1), so the dot product is exactly
        # the cosine similarity — see the search() docstring.
        scored = [(_dot(query_embedding, record["embedding"]), record) for record in records]
        # Insertion order breaks ties so results stay reproducible.
        scored.sort(key=lambda pair: (-pair[0], pair[1]["index"]))

        return [
            {
                "id": record["id"],
                "content": record["content"],
                "metadata": dict(record["metadata"]),
                "score": score,
            }
            # "embedding" is dropped on purpose: a 1536-dim vector makes the
            # result unreadable when printed in a terminal.
            for score, record in scored[:top_k]
        ]

    def add_documents(self, docs: list[Document]) -> None:
        """
        Embed each document's content and store it.

        For ChromaDB: use collection.add(ids=[...], documents=[...], embeddings=[...])
        For in-memory: append dicts to self._store
        """
        # One Document == one record. Chunking happens outside the store.
        for doc in docs:
            self._store.append(self._make_record(doc))

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Find the top_k most similar documents to query.

        For in-memory: compute dot product of query embedding vs all stored embeddings.
        """
        return self._search_records(query, self._store, top_k)

    def get_collection_size(self) -> int:
        """Return the total number of stored chunks."""
        return len(self._store)

    def search_with_filter(self, query: str, top_k: int = 3, metadata_filter: dict = None) -> list[dict]:
        """
        Search with optional metadata pre-filtering.

        First filter stored chunks by metadata_filter, then run similarity search.
        """
        if not metadata_filter:
            candidates = self._store
        else:
            # Filter BEFORE searching. Taking top_k first and discarding
            # non-matches afterwards can leave zero results even when the store
            # still holds valid documents — the k slots were already taken by
            # documents that the filter then removes.
            candidates = [
                record
                for record in self._store
                if all(record["metadata"].get(key) == value for key, value in metadata_filter.items())
            ]

        # Same code path as search(), so the two can never disagree.
        return self._search_records(query, candidates, top_k)

    def delete_document(self, doc_id: str) -> bool:
        """
        Remove all chunks belonging to a document.

        Returns True if any chunks were removed, False otherwise.
        """
        size_before = len(self._store)
        self._store = [
            record for record in self._store if record["metadata"].get("doc_id") != doc_id
        ]
        return len(self._store) < size_before
