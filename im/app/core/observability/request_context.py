from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def set_request_id(value: str | None) -> None:
    _request_id.set(value)


def get_request_id() -> str | None:
    return _request_id.get()


def set_trace_id(value: str | None) -> None:
    _trace_id.set(value)


def get_trace_id() -> str | None:
    return _trace_id.get()


def generate_request_id() -> str:
    # Short, log-friendly identifier.
    import uuid

    return uuid.uuid4().hex[:16]


def generate_trace_id() -> str:
    import uuid

    return uuid.uuid4().hex
