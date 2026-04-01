import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAdaptivePolling } from "@/features/chat/hooks/use-adaptive-polling";

describe("useAdaptivePolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  describe("initial state", () => {
    it("should return initial state with default interval", () => {
      const callback = vi.fn();
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false }),
      );

      expect(result.current.currentInterval).toBe(3000);
      expect(result.current.errorCount).toBe(0);
      expect(result.current.isPolling).toBe(false);
    });

    it("should use custom interval when provided", () => {
      const callback = vi.fn();
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false, interval: 5000 }),
      );

      expect(result.current.currentInterval).toBe(5000);
    });

    it("should return trigger and resetInterval functions", () => {
      const callback = vi.fn();
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false }),
      );

      expect(typeof result.current.trigger).toBe("function");
      expect(typeof result.current.resetInterval).toBe("function");
    });
  });

  describe("polling start and stop", () => {
    it("should start polling when isActive becomes true", () => {
      const callback = vi.fn();
      const { result, rerender } = renderHook(
        ({ isActive }) => useAdaptivePolling({ callback, isActive }),
        { initialProps: { isActive: false } },
      );

      expect(callback).not.toHaveBeenCalled();

      rerender({ isActive: true });

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(callback).toHaveBeenCalledTimes(1);
    });

    it("should stop polling when isActive becomes false", () => {
      const callback = vi.fn();
      const { result, rerender } = renderHook(
        ({ isActive }) => useAdaptivePolling({ callback, isActive }),
        { initialProps: { isActive: true } },
      );

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      expect(callback).toHaveBeenCalledTimes(1);

      rerender({ isActive: false });

      act(() => {
        vi.advanceTimersByTime(3000);
      });

      // Callback should not be called again after stopping
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it("should clear existing interval when restarting", () => {
      const callback = vi.fn();
      const { rerender } = renderHook(
        ({ isActive }) =>
          useAdaptivePolling({ callback, isActive, interval: 2000 }),
        { initialProps: { isActive: true } },
      );

      act(() => {
        vi.advanceTimersByTime(2000);
      });

      expect(callback).toHaveBeenCalledTimes(1);

      // Stop and restart
      rerender({ isActive: false });
      rerender({ isActive: true });

      act(() => {
        vi.advanceTimersByTime(2000);
      });

      // Should have been called exactly twice (once before stop, once after restart)
      expect(callback).toHaveBeenCalledTimes(2);
    });
  });

  describe("exponential backoff", () => {
    it("should apply exponential backoff on errors", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 1000,
          backoffMultiplier: 2,
          maxInterval: 10000,
        }),
      );

      // First error
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.errorCount).toBe(1);
      expect(result.current.currentInterval).toBe(2000);

      // Second error
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.errorCount).toBe(2);
      expect(result.current.currentInterval).toBe(4000);
    });

    it("should respect maxInterval during backoff", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 1000,
          backoffMultiplier: 10,
          maxInterval: 5000,
        }),
      );

      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.currentInterval).toBe(5000);
    });

    it("should respect minInterval during backoff", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 100,
          backoffMultiplier: 0.5,
          minInterval: 80,
        }),
      );

      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.currentInterval).toBe(80);
    });

    it("should not apply backoff when enableBackoff is false", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 1000,
          enableBackoff: false,
        }),
      );

      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.errorCount).toBe(0);
      expect(result.current.currentInterval).toBe(1000);
    });

    it("should reset interval and error count on success after errors", async () => {
      let shouldFail = true;
      const callback = vi.fn().mockImplementation(() => {
        if (shouldFail) throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 1000,
          backoffMultiplier: 2,
        }),
      );

      // First call fails
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.errorCount).toBe(1);
      expect(result.current.currentInterval).toBe(2000);

      // Second call succeeds
      shouldFail = false;
      await act(async () => {
        await result.current.trigger();
      });

      // After success, the interval and error count are reset
      expect(result.current.errorCount).toBe(0);
      expect(result.current.currentInterval).toBe(1000);
    });
  });

  describe("resetInterval", () => {
    it("should reset interval to initial value", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          interval: 1000,
          backoffMultiplier: 2,
        }),
      );

      // Trigger error to increase interval
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.errorCount).toBe(1);

      // Reset - wrap in act since it triggers state updates
      act(() => {
        result.current.resetInterval();
      });

      expect(result.current.currentInterval).toBe(1000);
      expect(result.current.errorCount).toBe(0);
    });
  });

  describe("trigger", () => {
    it("should call callback and update isPolling state", async () => {
      const callback = vi.fn().mockResolvedValue(undefined);
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false }),
      );

      expect(result.current.isPolling).toBe(false);

      await act(async () => {
        await result.current.trigger();
      });

      expect(result.current.isPolling).toBe(false);
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it("should handle callback errors gracefully", async () => {
      const callback = vi.fn().mockRejectedValue(new Error("Test error"));
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false }),
      );

      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });

      expect(result.current.isPolling).toBe(false);
      expect(result.current.errorCount).toBe(1);
    });
  });

  describe("boundary conditions", () => {
    it("should apply backoff up to maxErrors then stop applying backoff", async () => {
      const callback = vi.fn().mockImplementation(() => {
        throw new Error("API error");
      });
      const { result } = renderHook(() =>
        useAdaptivePolling({
          callback,
          isActive: false,
          maxErrors: 3,
          interval: 1000,
          backoffMultiplier: 2,
          maxInterval: 10000,
        }),
      );

      // Trigger 1st error - should apply backoff
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });
      expect(result.current.errorCount).toBe(1);
      expect(result.current.currentInterval).toBe(2000);

      // Trigger 2nd error - should apply backoff
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });
      expect(result.current.errorCount).toBe(2);
      expect(result.current.currentInterval).toBe(4000);

      // Trigger 3rd error - should apply backoff (newCount <= maxErrors)
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });
      expect(result.current.errorCount).toBe(3);
      expect(result.current.currentInterval).toBe(8000);

      // Trigger 4th error - should NOT apply backoff (newCount > maxErrors)
      await act(async () => {
        try {
          await result.current.trigger();
        } catch {
          // Expected
        }
      });
      // Error count continues to increment (it's just that backoff stops)
      expect(result.current.errorCount).toBe(4);
      // Interval stays at the same value (no more backoff applied)
      expect(result.current.currentInterval).toBe(8000);
    });

    it("should handle very small intervals", () => {
      const callback = vi.fn();
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false, interval: 100 }),
      );

      expect(result.current.currentInterval).toBe(100);
    });

    it("should handle very large intervals", () => {
      const callback = vi.fn();
      const { result } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: false, interval: 60000 }),
      );

      expect(result.current.currentInterval).toBe(60000);
    });

    it("should cleanup interval on unmount", () => {
      const callback = vi.fn();
      const { unmount } = renderHook(() =>
        useAdaptivePolling({ callback, isActive: true, interval: 1000 }),
      );

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      expect(callback).toHaveBeenCalledTimes(1);

      unmount();

      act(() => {
        vi.advanceTimersByTime(1000);
      });

      // Callback should not be called again after unmount
      expect(callback).toHaveBeenCalledTimes(1);
    });
  });
});
