from pydantic import BaseModel

from app.schemas.enums import TaskRunStatus


class TaskRunResponse(BaseModel):
    status: TaskRunStatus = TaskRunStatus.ACCEPTED
    session_id: str
