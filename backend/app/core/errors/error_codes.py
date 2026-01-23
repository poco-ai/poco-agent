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
    MCP_SERVER_NOT_FOUND = (12001, "MCP server not found")
    MCP_SERVER_ALREADY_EXISTS = (12002, "MCP server already exists")
    SKILL_NOT_FOUND = (13001, "Skill not found")
    SKILL_ALREADY_EXISTS = (13002, "Skill already exists")
    SKILL_MODIFY_FORBIDDEN = (13003, "Skill modification forbidden")
    PROJECT_NOT_FOUND = (14001, "Project not found")

    INTERNAL_ERROR = (50000, "Internal server error")
    DATABASE_ERROR = (50101, "Database operation failed")
    EXTERNAL_SERVICE_ERROR = (50201, "External service error")

    @property
    def code(self) -> int:
        return self.value[0]

    @property
    def message(self) -> str:
        return self.value[1]
