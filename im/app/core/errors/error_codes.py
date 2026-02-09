from enum import Enum


class ErrorCode(Enum):
    BAD_REQUEST = (40000, "Bad request")
    FORBIDDEN = (40300, "Forbidden")
    NOT_FOUND = (40400, "Not found")

    INTERNAL_ERROR = (50000, "Internal server error")
    EXTERNAL_SERVICE_ERROR = (50201, "External service error")

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]
