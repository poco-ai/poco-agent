from enum import Enum


class ErrorCode(Enum):
    BAD_REQUEST = (40000, "Bad request")
    UNAUTHORIZED = (40100, "Unauthorized")
    FORBIDDEN = (40300, "Forbidden")
    NOT_FOUND = (40400, "Resource not found")

    USER_NOT_FOUND = (10001, "User not found")
    USER_ALREADY_EXISTS = (10002, "User already exists")
    INVALID_CREDENTIALS = (10003, "Invalid credentials")

    BALANCE_INSUFFICIENT = (10101, "Insufficient balance")
    OPERATION_NOT_ALLOWED = (10102, "Operation not allowed")
    ENV_VAR_NOT_FOUND = (11001, "Environment variable not found")
    ENV_VAR_ALREADY_EXISTS = (11002, "Environment variable already exists")
    MCP_PRESET_NOT_FOUND = (12001, "MCP preset not found")
    MCP_PRESET_CREATE_FORBIDDEN = (12002, "MCP preset creation forbidden")
    SKILL_PRESET_NOT_FOUND = (13001, "Skill preset not found")
    SKILL_PRESET_CREATE_FORBIDDEN = (13002, "Skill preset creation forbidden")

    INTERNAL_ERROR = (50000, "Internal server error")
    DATABASE_ERROR = (50101, "Database operation failed")
    EXTERNAL_SERVICE_ERROR = (50201, "External service error")

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]
