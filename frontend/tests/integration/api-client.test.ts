import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  apiClient,
  getApiBaseUrl,
  API_PREFIX,
  apiFetch,
} from "@/services/api-client";
import { ApiError } from "@/lib/errors";

// Create a proper mock for fetch
const createMockResponse = (
  data: unknown,
  ok = true,
  status = 200,
): Response => {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Error",
    headers: new Headers({ "content-type": "application/json" }),
    json: async () => data,
    text: async () => JSON.stringify(data),
    blob: async () => new Blob(),
    arrayBuffer: async () => new ArrayBuffer(0),
    body: null,
    bodyUsed: false,
    clone: vi.fn(),
    url: "",
    redirected: false,
    type: "basic" as ResponseType,
  } as unknown as Response;
};

describe("api-client", () => {
  const originalWindow = global.window;
  const originalFetch = global.fetch;

  beforeEach(() => {
    // Reset environment variables
    delete process.env.NEXT_PUBLIC_API_URL;
    delete process.env.BACKEND_URL;
    delete process.env.POCO_BACKEND_URL;
  });

  afterEach(() => {
    // Restore window and fetch
    global.window = originalWindow;
    global.fetch = originalFetch;
  });

  describe("getApiBaseUrl", () => {
    it("should return empty string when no API URL is configured in browser", () => {
      // Mock browser environment
      Object.defineProperty(global, "window", {
        value: {},
        writable: true,
      });

      const baseUrl = getApiBaseUrl();
      expect(baseUrl).toBe("");
    });

    it("should throw ApiError when server-side URL is not configured", () => {
      // Mock server environment (no window)
      Object.defineProperty(global, "window", {
        value: undefined,
        writable: true,
      });

      expect(() => getApiBaseUrl()).toThrow(ApiError);
      expect(() => getApiBaseUrl()).toThrow("API base URL is not configured");
    });

    it("should use BACKEND_URL on server-side", () => {
      Object.defineProperty(global, "window", {
        value: undefined,
        writable: true,
      });
      process.env.BACKEND_URL = "http://backend:8000";

      const baseUrl = getApiBaseUrl();
      expect(baseUrl).toBe("http://backend:8000");
    });

    it("should prefer BACKEND_URL over POCO_BACKEND_URL", () => {
      Object.defineProperty(global, "window", {
        value: undefined,
        writable: true,
      });
      process.env.BACKEND_URL = "http://backend:8000";
      process.env.POCO_BACKEND_URL = "http://poco:8000";

      const baseUrl = getApiBaseUrl();
      expect(baseUrl).toBe("http://backend:8000");
    });
  });

  describe("API_PREFIX", () => {
    it("should be /api/v1", () => {
      expect(API_PREFIX).toBe("/api/v1");
    });
  });

  describe("apiFetch", () => {
    beforeEach(() => {
      Object.defineProperty(global, "window", {
        value: {},
        writable: true,
      });
      process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
    });

    it("should construct correct URL with endpoint", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(
          createMockResponse({ code: 200, data: { result: "success" } }),
        );

      await apiFetch("/test");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/test"),
        expect.objectContaining({
          headers: expect.any(Headers),
        }),
      );
    });

    it("should add Content-Type for non-FormData requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiFetch("/test", { method: "POST", body: { foo: "bar" } });

      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = callArgs[1]?.headers as Headers;
      expect(headers.get("Content-Type")).toBe("application/json");
    });

    it("should NOT add Content-Type for FormData requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      const formData = new FormData();
      formData.append("file", "content");

      await apiFetch("/upload", { method: "POST", body: formData });

      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = callArgs[1]?.headers as Headers;
      expect(headers.get("Content-Type")).toBeNull();
    });

    it("should unwrap standard API envelope on success", async () => {
      const mockData = { id: 1, name: "Test" };
      global.fetch = vi
        .fn()
        .mockResolvedValue(
          createMockResponse({ code: 200, message: "OK", data: mockData }),
        );

      const result = await apiFetch("/test");

      expect(result).toEqual(mockData);
    });

    it("should unwrap envelope with code 0", async () => {
      const mockData = { id: 1, name: "Test" };
      global.fetch = vi
        .fn()
        .mockResolvedValue(
          createMockResponse({ code: 0, message: "OK", data: mockData }),
        );

      const result = await apiFetch("/test");

      expect(result).toEqual(mockData);
    });

    it("should throw ApiError for non-200 code in envelope", async () => {
      global.fetch = vi.fn().mockResolvedValue(
        createMockResponse({
          code: 500,
          message: "Server Error",
          data: null,
        }),
      );

      await expect(apiFetch("/test")).rejects.toThrow(ApiError);
      await expect(apiFetch("/test")).rejects.toThrow("Server Error");
    });

    it("should throw ApiError for HTTP errors", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(
          createMockResponse({ message: "Resource not found" }, false, 404),
        );

      await expect(apiFetch("/test")).rejects.toThrow(ApiError);
      await expect(apiFetch("/test")).rejects.toThrow("Resource not found");
    });

    it("should throw ApiError with 408 status on AbortError", async () => {
      global.fetch = vi
        .fn()
        .mockRejectedValue(
          new DOMException("The operation was aborted", "AbortError"),
        );

      await expect(apiFetch("/test")).rejects.toThrow(ApiError);
      await expect(apiFetch("/test")).rejects.toThrow("Request timeout");

      try {
        await apiFetch("/test");
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).statusCode).toBe(408);
      }
    });

    it("should rethrow non-AbortError errors", async () => {
      const networkError = new Error("Network failure");
      global.fetch = vi.fn().mockRejectedValue(networkError);

      await expect(apiFetch("/test")).rejects.toThrow("Network failure");
    });

    it("should handle non-JSON responses", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
        headers: new Headers({ "content-type": "text/plain" }),
        json: async () => {
          throw new Error("Not JSON");
        },
        text: async () => "plain text response",
        blob: async () => new Blob(),
        arrayBuffer: async () => new ArrayBuffer(0),
        body: null,
        bodyUsed: false,
        clone: vi.fn(),
        url: "",
        redirected: false,
        type: "basic" as ResponseType,
      } as unknown as Response);

      const result = await apiFetch("/text");

      expect(result).toBe("plain text response");
    });

    it("should pass through fetch options", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      const controller = new AbortController();
      await apiFetch("/test", {
        method: "POST",
        signal: controller.signal,
        headers: { "X-Custom-Header": "value" },
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          signal: controller.signal,
        }),
      );
    });
  });

  describe("apiClient", () => {
    beforeEach(() => {
      Object.defineProperty(global, "window", {
        value: {},
        writable: true,
      });
      process.env.NEXT_PUBLIC_API_URL = "https://api.example.com";
    });

    afterEach(() => {
      global.fetch = originalFetch;
    });

    it("should make GET requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiClient.get("/test");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: "GET" }),
      );
    });

    it("should make POST requests with body", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiClient.post("/test", { foo: "bar" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("foo"),
        }),
      );
    });

    it("should make PATCH requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiClient.patch("/test", { update: "value" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "PATCH",
        }),
      );
    });

    it("should make PUT requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiClient.put("/test", { replace: "value" });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "PUT",
        }),
      );
    });

    it("should make DELETE requests", async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockResponse({ code: 200, data: null }));

      await apiClient.delete("/test");

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });
});
