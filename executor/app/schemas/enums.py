from enum import Enum


class FileStatus(str, Enum):
    """File change status in Git."""

    MODIFIED = "modified"
    STAGED = "staged"
    DELETED = "deleted"
    RENAMED = "renamed"


class TodoStatus(str, Enum):
    """Status of a todo item."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class CallbackStatus(str, Enum):
    """Status of agent execution callback."""

    ACCEPTED = "accepted"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRunStatus(str, Enum):
    """Status of a task run."""

    ACCEPTED = "accepted"
