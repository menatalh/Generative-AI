from typing import Literal

from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

SearchMode = Literal["hybrid", "keyword", "semantic"]
SEARCH_MODES: tuple[SearchMode, ...] = ("hybrid", "keyword", "semantic")

class HybridRetriever(BaseRetriever):
    """Retrieve chunks by keyword (BM25), semantic (vector) search, or both fused with Reciprocal Rank Fusion"""
    vectorstore: Chroma
    mode: SearchMode = "hybrid"
    k: int = 4
    fetch_k: int = 10  # candidates per retriever before merging in hybrid mode
    rrf_k: int = 60    # standard RRF damping constant

    def _semantic(self, query: str, k: int) -> list[Document]:
        return self.vectorstore.similarity_search(query, k=k)

    def _keyword(self, query: str, k: int) -> list[Document]:
        """BM25 over every chunk in the Chroma collection, so both searches see the same corpus"""
        data = self.vectorstore.get(include=["documents", "metadatas"])
        docs = [Document(page_content=text, metadata=meta or {}) for text, meta in zip(data["documents"], data["metadatas"])]
        if not docs:
            return []
        return BM25Retriever.from_documents(docs, k=k).invoke(query)

    def _merge(self, *rankings: list[Document]) -> list[Document]:
        """Reciprocal Rank Fusion: score = sum of 1 / (rrf_k + rank) across rankings"""
        scores: dict[str, float] = {}
        by_key: dict[str, Document] = {}
        for ranking in rankings:
            for rank, doc in enumerate(ranking, start=1):
                key = doc.page_content
                scores[key] = scores.get(key, 0.0) + 1 / (self.rrf_k + rank)
                by_key.setdefault(key, doc)
        best = sorted(scores, key=scores.get, reverse=True)[: self.k]
        return [by_key[key] for key in best]

    def _get_relevant_documents(self, query: str) -> list[Document]:
        if self.mode == "semantic":
            return self._semantic(query, self.k)
        if self.mode == "keyword":
            return self._keyword(query, self.k)
        return self._merge(self._semantic(query, self.fetch_k), self._keyword(query, self.fetch_k))
