from typing import TypedDict


class ErrorPayload(TypedDict, total=False):
    source: str
    operation: str
    error_type: str
    message: str
    status_code: int


def make_error_payload(
    *,
    source: str,
    operation: str,
    error: Exception | str,
    status_code: int | None = None,
) -> ErrorPayload:
    if isinstance(error, Exception):
        error_type = type(error).__name__
        message = str(error)
    else:
        error_type = "Error"
        message = error

    payload: ErrorPayload = {
        "source": source,
        "operation": operation,
        "error_type": error_type,
        "message": message,
    }
    if status_code is not None:
        payload["status_code"] = status_code
    return payload
