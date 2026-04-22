/**
 * Base application error class with error codes
 */
export class AppError extends Error {
  code: string;
  statusCode: number;

  constructor(message: string, code: string, statusCode: number = 400) {
    super(message);
    this.name = "AppError";
    this.code = code;
    this.statusCode = statusCode;
    Error.captureStackTrace?.(this, AppError);
  }

  toJSON() {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      statusCode: this.statusCode,
    };
  }
}

/**
 * Network-related errors
 */
export class NetworkError extends AppError {
  constructor(message: string, statusCode?: number) {
    super(message, "NETWORK_ERROR", statusCode || 503);
    this.name = "NetworkError";
  }
}

/**
 * API request errors
 */
export class ApiError extends AppError {
  statusCode: number;
  details?: unknown;

  constructor(message: string, statusCode: number, details?: unknown) {
    super(message, "API_ERROR", statusCode);
    this.name = "ApiError";
    this.statusCode = statusCode;
    this.details = details;
  }
}

/**
 * Validation errors
 */
export class ValidationError extends AppError {
  field?: string;

  constructor(message: string, field?: string) {
    super(message, "VALIDATION_ERROR", 400);
    this.name = "ValidationError";
    this.field = field;
  }
}

/**
 * Authentication errors
 */
export class AuthenticationError extends AppError {
  constructor(message: string = "Authentication failed") {
    super(message, "AUTH_ERROR", 401);
    this.name = "AuthenticationError";
  }
}

/**
 * Authorization errors
 */
export class AuthorizationError extends AppError {
  constructor(message: string = "Permission denied") {
    super(message, "AUTHZ_ERROR", 403);
    this.name = "AuthorizationError";
  }
}

/**
 * Not found errors
 */
export class NotFoundError extends AppError {
  constructor(resource: string = "Resource") {
    super(`${resource} not found`, "NOT_FOUND", 404);
    this.name = "NotFoundError";
  }
}

/**
 * Rate limit errors
 */
export class RateLimitError extends AppError {
  constructor(message: string = "Rate limit exceeded") {
    super(message, "RATE_LIMIT_ERROR", 429);
    this.name = "RateLimitError";
  }
}

/**
 * Error code constants
 */
export const ErrorCodes = {
  // Network & API
  NETWORK_ERROR: "NETWORK_ERROR",
  API_ERROR: "API_ERROR",
  TIMEOUT: "TIMEOUT",

  // Auth
  AUTH_ERROR: "AUTH_ERROR",
  AUTHZ_ERROR: "AUTHZ_ERROR",
  TOKEN_EXPIRED: "TOKEN_EXPIRED",

  // Client errors
  VALIDATION_ERROR: "VALIDATION_ERROR",
  NOT_FOUND: "NOT_FOUND",
  RATE_LIMIT_ERROR: "RATE_LIMIT_ERROR",

  // Server errors
  INTERNAL_ERROR: "INTERNAL_ERROR",
  SERVICE_UNAVAILABLE: "SERVICE_UNAVAILABLE",
} as const;

export type ErrorCode = (typeof ErrorCodes)[keyof typeof ErrorCodes];
