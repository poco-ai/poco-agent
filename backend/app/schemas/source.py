from typing import Literal

from pydantic import BaseModel


SourceKind = Literal[
    "github",
    "zip",
    "system",
    "manual",
    "unknown",
    "skill-creator",
    "marketplace",
]


class SourceInfo(BaseModel):
    kind: SourceKind
    market: str | None = None
    repo: str | None = None
    url: str | None = None
    ref: str | None = None
    filename: str | None = None
