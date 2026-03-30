import os
from dataclasses import dataclass

from .constants import BLABLADOR_DEFAULT_BASE_URL

DEFAULT_BLABLADOR_BASE_URL = BLABLADOR_DEFAULT_BASE_URL
DEFAULT_LLM_MODEL = "alias-fast"
LLM_CHAT_COMPLETIONS_PATH = "chat/completions"


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class LLMRuntimeConfig:
    api_key: str
    base_url: str
    model: str
    timeout_s: int
    retries: int
    max_input_chars: int


def load_llm_runtime_config() -> LLMRuntimeConfig:
    return LLMRuntimeConfig(
        api_key=os.getenv("BLABLADOR_API_KEY", ""),
        base_url=os.getenv("BLABLADOR_BASE_URL", DEFAULT_BLABLADOR_BASE_URL).rstrip(
            "/"
        ),
        model=os.getenv("KAIGRAPH_LLM_MODEL", DEFAULT_LLM_MODEL),
        timeout_s=_int_env("KAIGRAPH_LLM_TIMEOUT_S", 60, minimum=5, maximum=300),
        retries=_int_env("KAIGRAPH_LLM_RETRIES", 2, minimum=0, maximum=6),
        max_input_chars=_int_env(
            "KAIGRAPH_LLM_MAX_INPUT_CHARS",
            120_000,
            minimum=2_000,
            maximum=300_000,
        ),
    )


def llm_enabled(config: LLMRuntimeConfig) -> bool:
    return bool(config.api_key)


def llm_backend_label(config: LLMRuntimeConfig) -> str:
    if llm_enabled(config):
        return f"Blablador model={config.model}"
    return "heuristic fallback (BLABLADOR_API_KEY not set)"


def llm_chat_completions_url_from_base(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/{LLM_CHAT_COMPLETIONS_PATH}"


def llm_chat_completions_url(config: LLMRuntimeConfig) -> str:
    return llm_chat_completions_url_from_base(config.base_url)
