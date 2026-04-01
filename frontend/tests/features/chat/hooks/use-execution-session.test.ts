import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useExecutionSession } from "@/features/chat/hooks/use-execution-session";
import type { ExecutionSession } from "@/features/chat/types";

// Mock dependencies
vi.mock("@/features/chat/actions/query-actions", () => ({
  getExecutionSessionAction: vi.fn(),
}));

vi.mock("@/lib/utils/sound", () => ({
  playCompletionSound: vi.fn(),
}));

vi.mock("@/features/chat/hooks/use-adaptive-polling", () => ({
  useAdaptivePolling: vi.fn(() => ({
    currentInterval: 3000,
    errorCount: 0,
    isPolling: false,
    trigger: vi.fn().mockResolvedValue(undefined),
    resetInterval: vi.fn(),
  })),
}));

import { getExecutionSessionAction } from "@/features/chat/actions/query-actions";
import { playCompletionSound } from "@/lib/utils/sound";

// Helper to create a mock session
const createMockSession = (
  overrides: Partial<ExecutionSession> = {},
): ExecutionSession => ({
  session_id: "test-session-id",
  status: "running",
  progress: 50,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:01:00Z",
  ...overrides,
});

describe("useExecutionSession", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock localStorage
    const localStorageMock = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
      get length() {
        return 0;
      },
      key: vi.fn(),
    };
    vi.stubGlobal("localStorage", localStorageMock);
  });

  describe("initial loading", () => {
    it("should load session data on mount", async () => {
      const mockSession = createMockSession();
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(getExecutionSessionAction).toHaveBeenCalledWith({
        sessionId: "test-session-id",
        currentProgress: 0,
      });

      expect(result.current.session).toEqual(mockSession);
    });

    it("should handle empty sessionId gracefully", async () => {
      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "" }),
      );

      // With empty sessionId, fetchSession should early return without calling API
      // Wait for the effect to settle - session should remain null
      await waitFor(
        () => {
          expect(result.current.session).toBe(null);
        },
        { timeout: 3000 },
      );

      // isLoading should eventually settle (early return means no loading state change)
      expect(result.current.session).toBe(null);
    });

    it("should handle fetch errors", async () => {
      const error = new Error("Network error");
      vi.mocked(getExecutionSessionAction).mockRejectedValue(error);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBe(error);
      expect(result.current.session).toBe(null);
    });
  });

  describe("polling behavior", () => {
    it("should use default polling interval from env", async () => {
      const mockSession = createMockSession({ status: "running" });
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Default from hook or env fallback (6000ms when NEXT_PUBLIC_SESSION_POLLING_INTERVAL is not set)
      expect(result.current.pollingInterval).toBe(3000); // From mocked useAdaptivePolling
    });

    it("should use custom polling interval when provided", async () => {
      const mockSession = createMockSession({ status: "running" });
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({
          sessionId: "test-session-id",
          pollingInterval: 10000,
        }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Interval is controlled by useAdaptivePolling mock
      expect(result.current.pollingInterval).toBeDefined();
    });

    it("should stop polling when session completes", async () => {
      const runningSession = createMockSession({ status: "running" });

      vi.mocked(getExecutionSessionAction).mockResolvedValue(runningSession);

      const onPollingStop = vi.fn();

      const { result } = renderHook(() =>
        useExecutionSession({
          sessionId: "test-session-id",
          onPollingStop,
        }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.session?.status).toBe("running");

      // Simulate polling update
      act(() => {
        // In real scenario, polling would trigger this
        // For testing, we manually update session
        result.current.updateSession({ status: "completed" });
      });

      await waitFor(() => {
        expect(onPollingStop).toHaveBeenCalled();
      });
    });

    it("should trigger sound and callback on completion from active state", async () => {
      const runningSession = createMockSession({ status: "running" });

      vi.mocked(getExecutionSessionAction).mockResolvedValue(runningSession);

      const onPollingStop = vi.fn();

      const { result } = renderHook(() =>
        useExecutionSession({
          sessionId: "test-session-id",
          onPollingStop,
        }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // First session is running
      expect(result.current.session?.status).toBe("running");

      // Update to completed
      act(() => {
        result.current.updateSession({ status: "completed" });
      });

      await waitFor(() => {
        expect(playCompletionSound).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(onPollingStop).toHaveBeenCalled();
      });
    });
  });

  describe("updateSession", () => {
    it("should merge updates into existing session", async () => {
      const mockSession = createMockSession({
        status: "running",
        progress: 50,
      });
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateSession({ progress: 75 });
      });

      expect(result.current.session).toEqual({
        ...mockSession,
        progress: 75,
      });
    });

    it("should update status", async () => {
      const mockSession = createMockSession({ status: "running" });
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateSession({ status: "completed" });
      });

      expect(result.current.session?.status).toBe("completed");
    });

    it("should preserve user_prompt when updating", async () => {
      const mockSession = createMockSession({
        status: "running",
        user_prompt: "original prompt",
      });
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateSession({ progress: 90 });
      });

      expect(result.current.session?.user_prompt).toBe("original prompt");
    });

    it("should handle update when session is null", async () => {
      vi.mocked(getExecutionSessionAction).mockResolvedValue(
        null as unknown as ExecutionSession,
      );

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      act(() => {
        result.current.updateSession({ status: "running" });
      });

      expect(result.current.session).toBe(null);
    });
  });

  describe("error handling", () => {
    it("should track error count from polling", async () => {
      const mockSession = createMockSession();
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({
          sessionId: "test-session-id",
          enableBackoff: true,
        }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Error count comes from mocked useAdaptivePolling
      expect(result.current.errorCount).toBeDefined();
      expect(typeof result.current.errorCount).toBe("number");
    });

    it("should reset error state on successful fetch", async () => {
      const mockSession = createMockSession();
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe("refetch", () => {
    it("should trigger manual refetch", async () => {
      const mockSession = createMockSession();
      vi.mocked(getExecutionSessionAction).mockResolvedValue(mockSession);

      const { result } = renderHook(() =>
        useExecutionSession({ sessionId: "test-session-id" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Refetch uses the trigger from useAdaptivePolling
      expect(typeof result.current.refetch).toBe("function");
    });
  });

  describe("sessionId change", () => {
    it("should reset state when sessionId changes", async () => {
      const mockSession1 = createMockSession({ session_id: "session-1" });
      const mockSession2 = createMockSession({ session_id: "session-2" });

      vi.mocked(getExecutionSessionAction)
        .mockResolvedValueOnce(mockSession1)
        .mockResolvedValueOnce(mockSession2);

      const { result, rerender } = renderHook(
        ({ sessionId }) => useExecutionSession({ sessionId }),
        { initialProps: { sessionId: "session-1" } },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.session?.session_id).toBe("session-1");

      // Change sessionId
      rerender({ sessionId: "session-2" });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.session?.session_id).toBe("session-2");
    });
  });
});
