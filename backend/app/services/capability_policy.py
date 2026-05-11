from typing import Any


def resolve_effective_enabled(
    *,
    force_enabled: bool,
    default_enabled: bool,
    install_enabled: bool | None = None,
    override_enabled: bool | None = None,
) -> bool:
    """Resolve the effective enabled state for a capability."""
    if force_enabled:
        return True
    if override_enabled is not None:
        return override_enabled
    if install_enabled is not None:
        return install_enabled
    return default_enabled


def extract_override_enabled(
    overrides: dict[str, bool] | None,
    capability_id: int,
) -> bool | None:
    """Return the explicit override value for a capability id when present."""
    if not overrides:
        return None
    return overrides.get(str(capability_id))


def normalize_override_map(value: Any) -> dict[str, bool] | None:
    """Normalize a raw override map into ``{id: enabled}`` form."""
    if not isinstance(value, dict):
        return None

    normalized: dict[str, bool] = {}
    for raw_key, raw_enabled in value.items():
        if isinstance(raw_key, int):
            key = str(raw_key)
        elif isinstance(raw_key, str):
            key = raw_key.strip()
        else:
            continue

        if not key or not isinstance(raw_enabled, bool):
            continue
        normalized[key] = raw_enabled
    return normalized
