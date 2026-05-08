from m2s3om_graph.rdamsc.contracts import llm_diagnostics_template, result_is_ok


def test_llm_diagnostics_template_builds_expected_defaults() -> None:
    diagnostics = llm_diagnostics_template(
        timeout_s=45, retries=3, max_input_chars=5000
    )
    assert diagnostics == {
        "backend": "heuristic",
        "prompt_chars": 0,
        "llm_error": None,
        "candidates_before_validation": 0,
        "candidates_after_validation": 0,
        "timeout_s": 45,
        "retries": 3,
        "max_input_chars": 5000,
        "attempts_json": 0,
        "attempts_relaxed": 0,
    }


def test_result_is_ok_handles_success_failure_and_missing_key() -> None:
    assert result_is_ok({"ok": True}) is True
    assert result_is_ok({"ok": False, "reason": "no_locations"}) is False
    assert result_is_ok({"reason": "no_locations"}) is False


def test_result_is_ok_accepts_pipeline_step_shape() -> None:
    assert result_is_ok({"ok": True, "step": "kg_backfill", "backfilled_rules": 4})
    assert not result_is_ok({"ok": False, "step": "failed"})
