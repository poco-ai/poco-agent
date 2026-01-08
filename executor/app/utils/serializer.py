import dataclasses
from typing import Any


def serialize_message(obj: Any) -> dict | list | str | int | float | bool | None:
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [serialize_message(item) for item in obj]

    if isinstance(obj, dict):
        return {k: serialize_message(v) for k, v in obj.items()}

    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        result: dict[str, Any] = {"_type": type(obj).__name__}
        for field in dataclasses.fields(obj):
            result[field.name] = serialize_message(getattr(obj, field.name))
        return result

    return str(obj)
