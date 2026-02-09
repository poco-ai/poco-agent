from typing import Any

from app.core.errors.error_codes import ErrorCode


class AppException(Exception):
    def __init__(
        self,
        *,
        error_code: ErrorCode,
        message: str | None = None,
        details: Any | None = None,
    ) -> None:
        self.error_code = error_code
        self.code = error_code.code
        self.message = message or error_code.message
        self.details = details
        super().__init__(self.message)
