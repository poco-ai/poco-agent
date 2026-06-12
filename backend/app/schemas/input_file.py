from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class InputFile(BaseModel):
    """User-provided input file or URL attachment."""

    id: str | None = None
    type: Literal["file", "url"] = "file"
    name: str
    source: str
    size: int | None = None
    content_type: str | None = None
    path: str | None = None


class FileReferenceRange(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class InputFileReferenceMetadata(BaseModel):
    input_file_id: str | None = Field(default=None, alias="inputFileId")
    size: int | None = None
    content_type: str | None = Field(default=None, alias="contentType")
    path: str | None = None

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class InputFileReference(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["input_file"] = "input_file"
    source: str = Field(min_length=1)
    inserted_text: str = Field(min_length=1, alias="insertedText")
    display_name: str = Field(min_length=1, alias="displayName")
    range: FileReferenceRange | None = None
    metadata: InputFileReferenceMetadata | None = None

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class WorkspaceFileReferenceMetadata(BaseModel):
    size: int | None = None
    content_type: str | None = Field(default=None, alias="contentType")
    source_kind: str | None = Field(default=None, alias="sourceKind")

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


class WorkspaceFileReference(BaseModel):
    id: str = Field(min_length=1)
    kind: Literal["workspace_file"] = "workspace_file"
    session_id: str = Field(min_length=1, alias="sessionId")
    path: str = Field(min_length=1)
    inserted_text: str = Field(min_length=1, alias="insertedText")
    display_name: str = Field(min_length=1, alias="displayName")
    range: FileReferenceRange | None = None
    metadata: WorkspaceFileReferenceMetadata | None = None

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)


FileReference = InputFileReference | WorkspaceFileReference
