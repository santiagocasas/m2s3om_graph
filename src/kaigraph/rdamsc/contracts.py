from typing import Literal, TypeAlias, TypedDict

StatusCode: TypeAlias = str

IngestFailureReason: TypeAlias = Literal[
    "crosswalk_not_found",
    "missing_msc_id",
    "no_locations",
    "artifacts_unreachable",
    "artifacts_unsupported",
    "missing_standards",
    "bundle_missing_after_ingest",
    "no_rules_extracted",
    "exception",
]

IngestStrategy: TypeAlias = Literal[
    "llm",
    "deterministic_pdf",
    "deterministic_html_loc",
    "deterministic_generic",
    "deterministic_generic_augmented",
]

LLMBackend: TypeAlias = Literal["heuristic", "llm_json", "llm_relaxed", "none"]


class LLMDiagnostics(TypedDict):
    backend: LLMBackend
    prompt_chars: int
    llm_error: str | None
    candidates_before_validation: int
    candidates_after_validation: int
    timeout_s: int
    retries: int
    max_input_chars: int
    attempts_json: int
    attempts_relaxed: int


def llm_diagnostics_template(
    *,
    timeout_s: int,
    retries: int,
    max_input_chars: int,
) -> LLMDiagnostics:
    return {
        "backend": "heuristic",
        "prompt_chars": 0,
        "llm_error": None,
        "candidates_before_validation": 0,
        "candidates_after_validation": 0,
        "timeout_s": timeout_s,
        "retries": retries,
        "max_input_chars": max_input_chars,
        "attempts_json": 0,
        "attempts_relaxed": 0,
    }


class ArtifactCheck(TypedDict, total=False):
    url: str
    extension: str
    location_type: str
    status: str
    resolved_url: str
    content_type: str
    text_chars: int
    error: str
    http_status: int | None


class IngestSuccessResult(TypedDict):
    ok: Literal[True]
    crosswalk_id: str
    inserted_rules: int
    total_rules: int
    artifact_documents: int
    artifact_chunks: int
    artifacts: list[str]
    skipped: list[str]
    artifact_checks: list[ArtifactCheck]
    strategy: IngestStrategy
    llm_augmented_rules: int
    deterministic_diagnostics: dict[str, object] | None
    llm_diagnostics: LLMDiagnostics | None
    sssom_path: str


class _IngestFailureRequired(TypedDict):
    ok: Literal[False]
    reason: str


class IngestFailureResult(_IngestFailureRequired, total=False):
    crosswalk_id: str
    skipped: list[str]
    artifact_checks: list[ArtifactCheck]
    inserted_rules: int
    artifact_documents: int
    artifact_chunks: int
    artifacts: list[str]
    strategy: IngestStrategy
    llm_augmented_rules: int
    deterministic_diagnostics: dict[str, object] | None
    llm_diagnostics: LLMDiagnostics | None
    error: str


IngestResult: TypeAlias = IngestSuccessResult | IngestFailureResult


class PipelineStepResult(TypedDict, total=False):
    ok: bool
    reason: str
    backfilled_rules: int
    step: str


PipelineResult: TypeAlias = IngestResult | PipelineStepResult


class PipelineProcessedItem(TypedDict):
    crosswalk_id: str
    result: PipelineResult


class BootstrapPipelineResult(TypedDict):
    synced: int
    processed: list[PipelineProcessedItem]
    status_file: str


class PipelineStatusEntry(TypedDict, total=False):
    crosswalk_id: str
    msc_id: str | None
    name: str
    status: StatusCode
    label: str
    updated_at: str
    result: PipelineResult


PipelineStatusMap: TypeAlias = dict[str, PipelineStatusEntry]


def result_is_ok(result: PipelineResult) -> bool:
    return bool(result.get("ok"))
