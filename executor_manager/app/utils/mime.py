import mimetypes
from pathlib import PurePath


TEXT_MIME_OVERRIDES = {
    ".cjs": "text/javascript",
    ".css": "text/css",
    ".cts": "text/typescript",
    ".js": "text/javascript",
    ".jsx": "text/jsx",
    ".mjs": "text/javascript",
    ".mts": "text/typescript",
    ".ts": "text/typescript",
    ".tsx": "text/tsx",
}


def guess_mime_type(filename: str) -> str | None:
    """Guess a MIME type, correcting common code-file misclassifications."""
    suffix = PurePath(filename).suffix.lower()
    if suffix in TEXT_MIME_OVERRIDES:
        return TEXT_MIME_OVERRIDES[suffix]
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type
