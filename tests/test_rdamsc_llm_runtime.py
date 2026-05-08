from m2s3om_graph.rdamsc.llm_runtime import (
    DEFAULT_BLABLADOR_BASE_URL,
    DEFAULT_LLM_MODEL,
    llm_backend_label,
    llm_chat_completions_url,
    llm_chat_completions_url_from_base,
    llm_enabled,
    load_llm_runtime_config,
)


def test_load_llm_runtime_config_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    monkeypatch.delenv("BLABLADOR_BASE_URL", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_MODEL", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_TIMEOUT_S", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_RETRIES", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_MAX_INPUT_CHARS", raising=False)

    config = load_llm_runtime_config()
    assert config.api_key == ""
    assert config.base_url == DEFAULT_BLABLADOR_BASE_URL
    assert config.model == DEFAULT_LLM_MODEL
    assert config.timeout_s == 60
    assert config.retries == 2
    assert config.max_input_chars == 120_000


def test_load_llm_runtime_config_applies_env_and_bounds(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "secret")
    monkeypatch.setenv("BLABLADOR_BASE_URL", "https://example.org/custom/")
    monkeypatch.setenv("M2S3OM_LLM_MODEL", "model-x")
    monkeypatch.setenv("M2S3OM_LLM_TIMEOUT_S", "999")
    monkeypatch.setenv("M2S3OM_LLM_RETRIES", "-5")
    monkeypatch.setenv("M2S3OM_LLM_MAX_INPUT_CHARS", "100")

    config = load_llm_runtime_config()
    assert config.api_key == "secret"
    assert config.base_url == "https://example.org/custom"
    assert config.model == "model-x"
    assert config.timeout_s == 300
    assert config.retries == 0
    assert config.max_input_chars == 2_000


def test_llm_enabled_and_backend_label(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_MODEL", raising=False)
    disabled = load_llm_runtime_config()
    assert llm_enabled(disabled) is False
    assert (
        llm_backend_label(disabled) == "heuristic fallback (BLABLADOR_API_KEY not set)"
    )

    monkeypatch.setenv("BLABLADOR_API_KEY", "secret")
    monkeypatch.setenv("M2S3OM_LLM_MODEL", "model-z")
    enabled = load_llm_runtime_config()
    assert llm_enabled(enabled) is True
    assert llm_backend_label(enabled) == "Blablador model=model-z"


def test_chat_completions_url_helpers(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_BASE_URL", "https://api.example.org/v1/")
    config = load_llm_runtime_config()
    assert llm_chat_completions_url_from_base("https://x.example/v1/") == (
        "https://x.example/v1/chat/completions"
    )
    assert (
        llm_chat_completions_url(config)
        == "https://api.example.org/v1/chat/completions"
    )
