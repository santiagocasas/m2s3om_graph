import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    db_url: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_DB_URL", "ws://localhost:8000/rpc")
    )
    db_namespace: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_DB_NS", "kaigraph")
    )
    db_name: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_DB_NAME", "crosswalk")
    )
    db_user: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_DB_USER", "").strip()
    )
    db_password: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_DB_PASSWORD", "").strip()
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast")
    )
    embeddings_model: str = field(
        default_factory=lambda: os.getenv(
            "KAIGRAPH_EMBEDDINGS_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        )
    )
    retrieval_top_k: int = field(
        default_factory=lambda: int(os.getenv("KAIGRAPH_RETRIEVAL_TOP_K", "8"))
    )
