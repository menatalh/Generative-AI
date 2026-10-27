from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    """Tunables in one place so providers and retrieval settings are easy to switch"""
    llm_model: str = "openai/gpt-oss-120b"
    temperature: float = 0.0
    embedding_model: str = "all-MiniLM-L6-v2"
    collection_name: str = "student-rag"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    k: int = 4
    fetch_k: int = 10        # candidates per retriever before merging in hybrid mode
    max_file_mb: int = 20    # PDFs larger than this are skipped
