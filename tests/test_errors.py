from kaigraph.errors import make_error_payload


def test_make_error_payload_from_exception_with_status() -> None:
    payload = make_error_payload(
        source="rdamsc",
        operation="fetch_mapping",
        error=ValueError("bad input"),
        status_code=502,
    )
    assert payload == {
        "source": "rdamsc",
        "operation": "fetch_mapping",
        "error_type": "ValueError",
        "message": "bad input",
        "status_code": 502,
    }


def test_make_error_payload_from_string_without_status() -> None:
    payload = make_error_payload(
        source="candidate_suggestions",
        operation="parse_response",
        error="invalid schema",
    )
    assert payload == {
        "source": "candidate_suggestions",
        "operation": "parse_response",
        "error_type": "Error",
        "message": "invalid schema",
    }
