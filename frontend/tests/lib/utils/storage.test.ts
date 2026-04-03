import { describe, it, expect, beforeEach } from "vitest";
import {
  getLocalStorage,
  setLocalStorage,
  removeLocalStorage,
  clearLocalStorage,
  getSessionStorage,
  setSessionStorage,
  removeSessionStorage,
} from "@/lib/utils/storage";

describe("storage - localStorage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  describe("setLocalStorage", () => {
    it("stores value with poco_ prefix", () => {
      setLocalStorage("session_prompt", "test value");
      expect(localStorage.getItem("poco_session_prompt")).toBe('"test value"');
    });

    it("stores objects as JSON", () => {
      const obj = { key: "value", nested: { foo: "bar" } };
      setLocalStorage("user_preferences", obj);
      expect(localStorage.getItem("poco_user_preferences")).toBe(
        JSON.stringify(obj),
      );
    });

    it("handles arrays correctly", () => {
      const arr = [1, 2, 3];
      setLocalStorage("chat_history", arr);
      expect(localStorage.getItem("poco_chat_history")).toBe(
        JSON.stringify(arr),
      );
    });
  });

  describe("getLocalStorage", () => {
    it("retrieves stored value", () => {
      localStorage.setItem("poco_session_prompt", JSON.stringify("my prompt"));
      expect(getLocalStorage("session_prompt")).toBe("my prompt");
    });

    it("retrieves stored objects", () => {
      const obj = { theme: "dark" };
      localStorage.setItem("poco_user_preferences", JSON.stringify(obj));
      expect(getLocalStorage("user_preferences")).toEqual(obj);
    });

    it("returns null for non-existent keys", () => {
      expect(getLocalStorage("session_prompt")).toBeNull();
    });

    it("returns null for corrupted JSON", () => {
      localStorage.setItem("poco_session_prompt", "invalid{json}");
      expect(getLocalStorage("session_prompt")).toBeNull();
    });
  });

  describe("removeLocalStorage", () => {
    it("removes stored value with poco_ prefix", () => {
      localStorage.setItem("poco_session_prompt", JSON.stringify("value"));
      removeLocalStorage("session_prompt");
      expect(localStorage.getItem("poco_session_prompt")).toBeNull();
    });

    it("does not throw when removing non-existent key", () => {
      expect(() => removeLocalStorage("session_prompt")).not.toThrow();
    });
  });

  describe("clearLocalStorage", () => {
    it("removes all poco_ prefixed entries", () => {
      localStorage.setItem("poco_session_prompt", "value1");
      localStorage.setItem("poco_user_preferences", "value2");
      localStorage.setItem("other_key", "should_remain");

      clearLocalStorage();

      expect(localStorage.getItem("poco_session_prompt")).toBeNull();
      expect(localStorage.getItem("poco_user_preferences")).toBeNull();
      expect(localStorage.getItem("other_key")).toBe("should_remain");
    });

    it("handles empty storage gracefully", () => {
      expect(() => clearLocalStorage()).not.toThrow();
    });
  });
});

describe("storage - sessionStorage", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  describe("setSessionStorage", () => {
    it("stores value with poco_ prefix", () => {
      setSessionStorage("temp_state", "temp value");
      expect(sessionStorage.getItem("poco_temp_state")).toBe('"temp value"');
    });
  });

  describe("getSessionStorage", () => {
    it("retrieves stored value", () => {
      sessionStorage.setItem("poco_temp_state", JSON.stringify("my state"));
      expect(getSessionStorage("temp_state")).toBe("my state");
    });

    it("returns null for non-existent keys", () => {
      expect(getSessionStorage("temp_state")).toBeNull();
    });

    it("returns null for corrupted JSON", () => {
      sessionStorage.setItem("poco_temp_state", "invalid{json}");
      expect(getSessionStorage("temp_state")).toBeNull();
    });
  });

  describe("removeSessionStorage", () => {
    it("removes stored value with poco_ prefix", () => {
      sessionStorage.setItem("poco_temp_state", JSON.stringify("value"));
      removeSessionStorage("temp_state");
      expect(sessionStorage.getItem("poco_temp_state")).toBeNull();
    });
  });
});

describe("storage - SSR behavior", () => {
  it("returns null when window is undefined (SSR)", () => {
    const originalWindow = global.window;
    // @ts-expect-error - intentionally removing window for SSR test
    delete global.window;

    expect(getLocalStorage("session_prompt")).toBeNull();
    expect(getSessionStorage("temp_state")).toBeNull();

    // Does not throw in SSR
    expect(() => setLocalStorage("session_prompt", "value")).not.toThrow();
    expect(() => setSessionStorage("temp_state", "value")).not.toThrow();

    global.window = originalWindow;
  });
});
