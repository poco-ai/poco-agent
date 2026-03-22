import re
from typing import Any

_FRONT_MATTER_DELIM = "---"
_MODEL_KEY_PATTERN = re.compile(r"^\s*model\s*:", re.IGNORECASE)


def parse_yaml_front_matter(markdown: str) -> dict[str, Any]:
    """Parse YAML front matter from a Markdown document.

    Returns a dictionary with front matter key-value pairs.
    Supports simple scalar values (strings, numbers, booleans).
    """
    if not markdown:
        return {}

    text = markdown[1:] if markdown.startswith("\ufeff") else markdown
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONT_MATTER_DELIM:
        return {}

    end_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONT_MATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        return {}

    front_lines = lines[1:end_idx]
    result: dict[str, Any] = {}
    i = 0

    while i < len(front_lines):
        line = front_lines[i]
        stripped = line.strip()

        # Skip empty lines and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        # Parse key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()

            # Handle block scalars (| or >)
            if value in ("", "|", ">"):
                # Collect indented lines
                indent = len(line) - len(line.lstrip())
                block_lines: list[str] = []
                i += 1
                while i < len(front_lines):
                    next_line = front_lines[i]
                    if not next_line.strip():
                        block_lines.append("")
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= indent:
                        break
                    block_lines.append(next_line.lstrip())
                    i += 1
                value = "\n".join(block_lines).strip()
            else:
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                # Convert to appropriate type
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
                i += 1

            result[key] = value
        else:
            i += 1

    return result


def remove_model_from_yaml_front_matter(markdown: str) -> str:
    """Remove `model` from YAML front matter in a Markdown document.

    This is a minimal sanitizer used to ensure user content cannot override the
    executor's DEFAULT_MODEL via front matter configuration.
    """
    if not markdown:
        return ""

    text = markdown[1:] if markdown.startswith("\ufeff") else markdown
    lines = text.splitlines()
    if not lines or lines[0].strip() != _FRONT_MATTER_DELIM:
        return markdown

    end_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FRONT_MATTER_DELIM:
            end_idx = i
            break
    if end_idx is None:
        return markdown

    front = lines[1:end_idx]
    body = lines[end_idx + 1 :]

    filtered_front: list[str] = []
    i = 0
    while i < len(front):
        line = front[i]
        if not _MODEL_KEY_PATTERN.match(line):
            filtered_front.append(line)
            i += 1
            continue

        # Drop `model` key. If it's a block value (e.g. `model:` / `model: |`), also
        # drop its indented continuation lines to avoid leaving invalid YAML behind.
        indent = len(line) - len(line.lstrip())
        remainder = line.split(":", 1)[1].strip() if ":" in line else ""
        is_block = remainder == "" or remainder.startswith(("|", ">"))
        i += 1
        if not is_block:
            continue
        while i < len(front):
            next_line = front[i]
            if not next_line.strip():
                i += 1
                continue
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= indent:
                break
            i += 1

    rebuilt = [_FRONT_MATTER_DELIM, *filtered_front, _FRONT_MATTER_DELIM, *body]
    return "\n".join(rebuilt).rstrip() + "\n"


def update_yaml_front_matter(
    markdown: str,
    updates: dict[str, Any],
) -> str:
    """Update or create YAML front matter fields in a Markdown document."""
    text = markdown[1:] if markdown.startswith("\ufeff") else markdown
    lines = text.splitlines()
    has_front_matter = bool(lines) and lines[0].strip() == _FRONT_MATTER_DELIM

    body_lines: list[str]
    front_matter = parse_yaml_front_matter(text)
    if has_front_matter:
        end_idx: int | None = None
        for i in range(1, len(lines)):
            if lines[i].strip() == _FRONT_MATTER_DELIM:
                end_idx = i
                break
        body_lines = lines[end_idx + 1 :] if end_idx is not None else []
    else:
        body_lines = lines

    for key, value in updates.items():
        if value is None:
            front_matter.pop(key, None)
            continue
        front_matter[key] = value

    rendered_front_matter = [
        f"{key}: {_render_yaml_scalar(value)}" for key, value in front_matter.items()
    ]
    rebuilt = [
        _FRONT_MATTER_DELIM,
        *rendered_front_matter,
        _FRONT_MATTER_DELIM,
        *body_lines,
    ]
    return "\n".join(rebuilt).rstrip() + "\n"


def _render_yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'
