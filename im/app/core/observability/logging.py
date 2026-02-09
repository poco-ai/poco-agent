import datetime as _dt
import json
import logging
import os
import sys
from typing import Any

from app.core.observability.request_context import get_request_id, get_trace_id

_installed_record_factory = False


def _parse_level(value: str | None, *, default: int) -> int:
    if not value:
        return default
    candidate = value.strip().upper()
    mapping = logging.getLevelNamesMapping()
    return mapping.get(candidate, default)


def _safe_value(key: str, value: Any) -> str:
    lowered = key.lower()
    if any(token in lowered for token in ("token", "secret", "password", "api_key")):
        return '"***"'

    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, (dict, list, tuple)):
        dumped = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        if len(dumped) > 800:
            dumped = dumped[:800] + "...(truncated)"
        return json.dumps(dumped, ensure_ascii=False)

    text = str(value).replace("\n", "\\n")
    if len(text) > 800:
        text = text[:800] + "...(truncated)"
    return json.dumps(text, ensure_ascii=False)


_STANDARD_ATTRS: set[str] = set(
    logging.LogRecord(
        name="x",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="x",
        args=(),
        exc_info=None,
    ).__dict__.keys()
)


class _KeyValueFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        dt = _dt.datetime.fromtimestamp(record.created, tz=_dt.timezone.utc)
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        service = getattr(record, "service", "-")
        request_id = getattr(record, "request_id", "-")
        trace_id = getattr(record, "trace_id", "-")

        base = (
            f"{self.formatTime(record)} {record.levelname} {service} {record.name} "
            f"[request_id={request_id} trace_id={trace_id}] {message}"
        )

        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in _STANDARD_ATTRS
            and not k.startswith("_")
            and k not in {"service", "request_id", "trace_id"}
        }
        if extras:
            extra_kv = " ".join(
                f"{k}={_safe_value(k, v)}" for k, v in sorted(extras.items())
            )
            base = f"{base} {extra_kv}"

        if record.exc_info:
            base = f"{base}\n{self.formatException(record.exc_info)}"

        return base


def configure_logging(
    *,
    debug: bool,
    service_name: str,
    access_log: bool | None = None,
) -> None:
    """Configure stdout logging with request/trace context ids."""
    global _installed_record_factory

    if access_log is None:
        access_log = os.getenv("UVICORN_ACCESS_LOG", "").strip().lower() in {
            "1",
            "true",
            "yes",
        }

    if not _installed_record_factory:
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.service = service_name
            record.request_id = get_request_id() or "-"
            record.trace_id = get_trace_id() or "-"
            return record

        logging.setLogRecordFactory(record_factory)
        _installed_record_factory = True

    default_level = logging.DEBUG if debug else logging.INFO
    level = _parse_level(os.getenv("LOG_LEVEL"), default=default_level)

    formatter = _KeyValueFormatter()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Uvicorn access logs are redundant once request logging middleware is enabled.
    logging.getLogger("uvicorn.access").setLevel(
        logging.INFO if access_log else logging.WARNING
    )
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers.clear()
        lg.propagate = True
