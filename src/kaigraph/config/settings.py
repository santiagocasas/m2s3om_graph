import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_url: str = os.getenv("KAIGRAPH_DB_URL", "ws://localhost:8000/rpc")
    db_namespace: str = os.getenv("KAIGRAPH_DB_NS", "kaigraph")
    db_name: str = os.getenv("KAIGRAPH_DB_NAME", "crosswalk")
    db_user: str = os.getenv("KAIGRAPH_DB_USER", "root")
    db_password: str = os.getenv("KAIGRAPH_DB_PASSWORD", "root")
    llm_model: str = os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast")
    embeddings_model: str = os.getenv(
        "KAIGRAPH_EMBEDDINGS_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    )
    retrieval_top_k: int = int(os.getenv("KAIGRAPH_RETRIEVAL_TOP_K", "8"))
