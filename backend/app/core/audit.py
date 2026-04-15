import inspect
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.settings import get_settings


@dataclass(slots=True)
class AuditEvent:
    workspace_id: Any
    actor_user_id: str
    action: str
    target_type: str
    target_id: str
    metadata: dict[str, Any]


class AuditConfig:
    def __init__(self, rules: dict[str, bool] | None = None) -> None:
        self._rules = rules or get_settings().audit_rules

    def is_enabled(self, action: str) -> bool:
        if action in self._rules:
            return self._rules[action]

        best_match: tuple[int, bool] | None = None
        for pattern, enabled in self._rules.items():
            if not pattern.endswith("*"):
                continue
            prefix = pattern[:-1]
            if not action.startswith(prefix):
                continue
            if best_match is None or len(prefix) > best_match[0]:
                best_match = (len(prefix), enabled)

        if best_match is not None:
            return best_match[1]

        return self._rules.get("default", True)


Resolver = Callable[[dict[str, Any], Any], Any]


def _resolve(value: Resolver | Any, bound_args: dict[str, Any], result: Any) -> Any:
    if callable(value):
        return value(bound_args, result)
    return value


def auditable(
    *,
    action: str,
    target_type: str,
    target_id: Resolver | Any,
    workspace_id: Resolver | Any,
    metadata_fn: Resolver | None = None,
) -> Callable:
    def decorator(func: Callable) -> Callable:
        signature = inspect.signature(func)

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            bound_args = dict(bound.arguments)
            db = bound_args.get("db")
            if not isinstance(db, Session):
                return result

            current_user = bound_args.get("current_user")
            actor_user_id = getattr(current_user, "id", None)
            if not actor_user_id:
                return result

            from app.services.activity_logger import ActivityLogger

            event = AuditEvent(
                workspace_id=_resolve(workspace_id, bound_args, result),
                actor_user_id=actor_user_id,
                action=action,
                target_type=target_type,
                target_id=str(_resolve(target_id, bound_args, result)),
                metadata=(
                    _resolve(metadata_fn, bound_args, result)
                    if metadata_fn is not None
                    else {}
                ),
            )
            ActivityLogger().log_activity(db, event)
            return result

        return wrapper

    return decorator
