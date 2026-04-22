/**
 * Global error handling utilities
 */

import {
  AppError,
  NetworkError,
  ApiError,
  RateLimitError,
} from "./app-error.ts";

/**
 * Parse API error response and create appropriate error
 */
export function parseApiError(
  error: unknown,
  defaultMessage: string = "An error occurred",
): AppError {
  // Already an AppError
  if (error instanceof AppError) {
    return error;
  }

  // API response with error structure
  if (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    "message" in error
  ) {
    const apiError = error as {
      code: number;
      message: string;
      details?: unknown;
    };
    return new ApiError(apiError.message, apiError.code, apiError.details);
  }

  // Fetch error
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return new NetworkError("Network request failed");
  }

  // Standard Error
  if (error instanceof Error) {
    return new AppError(error.message, "UNKNOWN_ERROR");
  }

  // Unknown error
  return new AppError(defaultMessage, "UNKNOWN_ERROR");
}

/**
 * Get user-friendly error message
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof AppError) {
    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "An unexpected error occurred";
}

/**
 * Log error to console (in development) or error tracking service
 */
export function logError(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  const errorInfo = {
    error,
    context,
    timestamp: new Date().toISOString(),
  };

  if (import.meta.env.DEV) {
    console.error("[Error]", errorInfo);
  }

  // TODO: Send to error tracking service (e.g., Sentry)
  // if (typeof window !== "undefined" && window.Sentry) {
  //   window.Sentry.captureException(error, { extra: context });
  // }
}

/**
 * Handle error with user notification
 */
export function handleError(
  error: unknown,
  options?: {
    defaultMessage?: string;
    showToast?: boolean;
    log?: boolean;
  },
): AppError {
  const appError = parseApiError(error, options?.defaultMessage);

  if (options?.log !== false) {
    logError(appError);
  }

  if (options?.showToast) {
    // TODO: Show toast notification
    // toast.error(appError.message);
  }

  return appError;
}

/**
 * Type guard to check if error is an AppError
 */
export function isAppError(error: unknown): error is AppError {
  return error instanceof AppError;
}

/**
 * Retry function with exponential backoff
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: {
    maxRetries?: number;
    baseDelay?: number;
    maxDelay?: number;
    shouldRetry?: (error: unknown) => boolean;
  } = {},
): Promise<T> {
  const {
    maxRetries = 3,
    baseDelay = 1000,
    maxDelay = 10000,
    shouldRetry = (error) =>
      error instanceof NetworkError || error instanceof RateLimitError,
  } = options;

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries || !shouldRetry(error)) {
        throw error;
      }

      const delay = Math.min(baseDelay * Math.pow(2, attempt), maxDelay);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}
