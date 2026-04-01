import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  AppError,
  NetworkError,
  ApiError,
  ValidationError,
  RateLimitError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ErrorCodes,
} from "@/lib/errors/app-error";
import {
  parseApiError,
  getErrorMessage,
  logError,
  handleError,
  isAppError,
  retryWithBackoff,
} from "@/lib/errors/error-handler";

describe("AppError classes", () => {
  describe("AppError", () => {
    it("creates base error with message, code, and default statusCode", () => {
      const error = new AppError("Something went wrong", "CUSTOM_ERROR");
      expect(error.message).toBe("Something went wrong");
      expect(error.code).toBe("CUSTOM_ERROR");
      expect(error.statusCode).toBe(400);
      expect(error.name).toBe("AppError");
    });

    it("accepts custom statusCode", () => {
      const error = new AppError("Error", "CODE", 500);
      expect(error.statusCode).toBe(500);
    });

    it("serializes to JSON correctly", () => {
      const error = new AppError("Message", "CODE", 422);
      expect(error.toJSON()).toEqual({
        name: "AppError",
        code: "CODE",
        message: "Message",
        statusCode: 422,
      });
    });
  });

  describe("NetworkError", () => {
    it("extends AppError with NETWORK_ERROR code", () => {
      const error = new NetworkError("Network failed");
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("NETWORK_ERROR");
      expect(error.statusCode).toBe(503);
      expect(error.name).toBe("NetworkError");
    });

    it("accepts custom statusCode", () => {
      const error = new NetworkError("Timeout", 504);
      expect(error.statusCode).toBe(504);
    });
  });

  describe("ApiError", () => {
    it("extends AppError with API_ERROR code", () => {
      const error = new ApiError("API failed", 500);
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("API_ERROR");
      expect(error.statusCode).toBe(500);
      expect(error.name).toBe("ApiError");
    });

    it("stores details", () => {
      const details = { field: "email", reason: "invalid" };
      const error = new ApiError("Validation failed", 400, details);
      expect(error.details).toEqual(details);
    });
  });

  describe("ValidationError", () => {
    it("extends AppError with VALIDATION_ERROR code", () => {
      const error = new ValidationError("Invalid input");
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("VALIDATION_ERROR");
      expect(error.statusCode).toBe(400);
    });

    it("stores field name", () => {
      const error = new ValidationError("Required", "email");
      expect(error.field).toBe("email");
    });
  });

  describe("RateLimitError", () => {
    it("extends AppError with RATE_LIMIT_ERROR code", () => {
      const error = new RateLimitError();
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("RATE_LIMIT_ERROR");
      expect(error.statusCode).toBe(429);
    });
  });

  describe("AuthenticationError", () => {
    it("extends AppError with AUTH_ERROR code", () => {
      const error = new AuthenticationError();
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("AUTH_ERROR");
      expect(error.statusCode).toBe(401);
    });

    it("accepts custom message", () => {
      const error = new AuthenticationError("Invalid token");
      expect(error.message).toBe("Invalid token");
    });
  });

  describe("AuthorizationError", () => {
    it("extends AppError with AUTHZ_ERROR code", () => {
      const error = new AuthorizationError();
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("AUTHZ_ERROR");
      expect(error.statusCode).toBe(403);
    });
  });

  describe("NotFoundError", () => {
    it("extends AppError with NOT_FOUND code", () => {
      const error = new NotFoundError();
      expect(error).toBeInstanceOf(AppError);
      expect(error.code).toBe("NOT_FOUND");
      expect(error.statusCode).toBe(404);
    });

    it("includes resource name in message", () => {
      const error = new NotFoundError("User");
      expect(error.message).toBe("User not found");
    });
  });

  describe("ErrorCodes", () => {
    it("contains all expected error codes", () => {
      expect(ErrorCodes.NETWORK_ERROR).toBe("NETWORK_ERROR");
      expect(ErrorCodes.API_ERROR).toBe("API_ERROR");
      expect(ErrorCodes.TIMEOUT).toBe("TIMEOUT");
      expect(ErrorCodes.AUTH_ERROR).toBe("AUTH_ERROR");
      expect(ErrorCodes.AUTHZ_ERROR).toBe("AUTHZ_ERROR");
      expect(ErrorCodes.TOKEN_EXPIRED).toBe("TOKEN_EXPIRED");
      expect(ErrorCodes.VALIDATION_ERROR).toBe("VALIDATION_ERROR");
      expect(ErrorCodes.NOT_FOUND).toBe("NOT_FOUND");
      expect(ErrorCodes.RATE_LIMIT_ERROR).toBe("RATE_LIMIT_ERROR");
      expect(ErrorCodes.INTERNAL_ERROR).toBe("INTERNAL_ERROR");
      expect(ErrorCodes.SERVICE_UNAVAILABLE).toBe("SERVICE_UNAVAILABLE");
    });
  });
});

describe("parseApiError", () => {
  it("returns AppError as-is", () => {
    const appError = new AppError("Error", "CODE", 400);
    expect(parseApiError(appError)).toBe(appError);
  });

  it("returns subclass of AppError as-is", () => {
    const networkError = new NetworkError("Failed");
    expect(parseApiError(networkError)).toBe(networkError);
  });

  it("creates ApiError from object with code and message", () => {
    const obj = {
      code: 500,
      message: "Server error",
      details: { key: "value" },
    };
    const parsed = parseApiError(obj);
    expect(parsed).toBeInstanceOf(ApiError);
    expect(parsed.statusCode).toBe(500);
    expect(parsed.message).toBe("Server error");
    expect((parsed as ApiError).details).toEqual({ key: "value" });
  });

  it("creates NetworkError from TypeError with fetch message", () => {
    const error = new TypeError("Failed to fetch");
    const parsed = parseApiError(error);
    expect(parsed).toBeInstanceOf(NetworkError);
    expect(parsed.message).toBe("Network request failed");
  });

  it("creates AppError from standard Error", () => {
    const error = new Error("Something failed");
    const parsed = parseApiError(error);
    expect(parsed).toBeInstanceOf(AppError);
    expect(parsed.code).toBe("UNKNOWN_ERROR");
    expect(parsed.message).toBe("Something failed");
  });

  it("creates AppError with default message for unknown error", () => {
    const parsed = parseApiError(null, "Custom error");
    expect(parsed).toBeInstanceOf(AppError);
    expect(parsed.message).toBe("Custom error");
    expect(parsed.code).toBe("UNKNOWN_ERROR");
  });

  it("creates AppError with default message for string error", () => {
    const parsed = parseApiError("string error");
    expect(parsed.message).toBe("An error occurred");
  });
});

describe("getErrorMessage", () => {
  it("returns message from AppError", () => {
    const error = new AppError("App error", "CODE");
    expect(getErrorMessage(error)).toBe("App error");
  });

  it("returns message from standard Error", () => {
    const error = new Error("Standard error");
    expect(getErrorMessage(error)).toBe("Standard error");
  });

  it("returns generic message for non-Error", () => {
    expect(getErrorMessage("string")).toBe("An unexpected error occurred");
    expect(getErrorMessage(null)).toBe("An unexpected error occurred");
  });
});

describe("logError", () => {
  it("logs error info in development", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const error = new AppError("Test error", "CODE");
    const context = { userId: "123", action: "test" };

    logError(error, context);

    expect(consoleSpy).toHaveBeenCalledWith("[Error]", {
      error,
      context,
      timestamp: expect.any(String),
    });

    consoleSpy.mockRestore();
  });

  it("handles errors without context", () => {
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    logError(new Error("Test"));

    expect(consoleSpy).toHaveBeenCalled();

    consoleSpy.mockRestore();
  });
});

describe("handleError", () => {
  it("parses error and returns AppError", () => {
    const result = handleError("string error");
    expect(result).toBeInstanceOf(AppError);
  });

  it("logs error by default", () => {
    const logSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    handleError(new Error("Test"));

    expect(logSpy).toHaveBeenCalled();

    logSpy.mockRestore();
  });

  it("skips logging when log is false", () => {
    const logSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    handleError(new Error("Test"), { log: false });

    expect(logSpy).not.toHaveBeenCalled();

    logSpy.mockRestore();
  });

  it("uses custom default message", () => {
    const result = handleError(null, { defaultMessage: "Custom error" });
    expect(result.message).toBe("Custom error");
  });
});

describe("isAppError", () => {
  it("returns true for AppError instances", () => {
    expect(isAppError(new AppError("Error", "CODE"))).toBe(true);
    expect(isAppError(new NetworkError("Failed"))).toBe(true);
    expect(isAppError(new ApiError("API", 500))).toBe(true);
  });

  it("returns false for non-AppError", () => {
    expect(isAppError(new Error("Error"))).toBe(false);
    expect(isAppError("string")).toBe(false);
    expect(isAppError(null)).toBe(false);
    expect(isAppError(undefined)).toBe(false);
  });

  it("narrows type correctly", () => {
    const error: unknown = new AppError("Error", "CODE");
    if (isAppError(error)) {
      // TypeScript should know error is AppError here
      expect(error.code).toBeDefined();
    } else {
      // This branch should not execute
      expect(true).toBe(false);
    }
  });
});

describe("retryWithBackoff", () => {
  beforeEach(() => {
    vi.useRealTimers(); // Use real timers to avoid async issues
  });

  it("returns result on first successful attempt", async () => {
    const fn = vi.fn().mockResolvedValue("success");
    const result = await retryWithBackoff(fn);
    expect(result).toBe("success");
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("retries on retryable error", async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new NetworkError("Failed"))
      .mockResolvedValue("success");

    const result = await retryWithBackoff(fn);
    expect(result).toBe("success");
    expect(fn).toHaveBeenCalledTimes(2);
  }, 10000);

  it("respects maxRetries limit", async () => {
    const fn = vi.fn().mockRejectedValue(new NetworkError("Failed"));

    await expect(retryWithBackoff(fn, { maxRetries: 2 })).rejects.toThrow(
      NetworkError,
    );
    expect(fn).toHaveBeenCalledTimes(3); // initial + 2 retries
  }, 10000);

  it("does not retry non-retryable errors", async () => {
    const fn = vi.fn().mockRejectedValue(new ValidationError("Invalid"));

    await expect(retryWithBackoff(fn)).rejects.toThrow(ValidationError);
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("uses custom shouldRetry function", async () => {
    const customError = new Error("Custom retryable");
    const fn = vi
      .fn()
      .mockRejectedValueOnce(customError)
      .mockResolvedValue("success");

    const shouldRetry = vi.fn().mockReturnValue(true);

    const result = await retryWithBackoff(fn, { shouldRetry });
    expect(result).toBe("success");
    expect(shouldRetry).toHaveBeenCalledWith(customError);
  }, 10000);

  it("uses exponential backoff with maxDelay cap", async () => {
    const fn = vi
      .fn()
      .mockRejectedValueOnce(new RateLimitError())
      .mockRejectedValueOnce(new RateLimitError())
      .mockRejectedValueOnce(new RateLimitError())
      .mockResolvedValue("success");

    const result = await retryWithBackoff(fn, {
      maxRetries: 5,
      baseDelay: 10, // Use small delay for faster tests
      maxDelay: 30,
    });

    expect(result).toBe("success");
    expect(fn).toHaveBeenCalledTimes(4);
  }, 10000);

  it("throws last error after exhausting retries", async () => {
    const lastError = new NetworkError("Last attempt failed");
    const fn = vi.fn().mockRejectedValue(lastError);

    await expect(retryWithBackoff(fn, { maxRetries: 2 })).rejects.toThrow(
      "Last attempt failed",
    );
  }, 10000);
});
