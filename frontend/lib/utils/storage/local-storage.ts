/**
 * LocalStorage wrapper with type safety and error handling.
 */
const PREFIX = "poco_";

export type StorageKey =
  | "session_prompt"
  | "user_preferences"
  | "draft_message"
  | "chat_history"
  | "connector_state";

/**
 * Read a value from localStorage.
 */
export function getLocalStorage<T>(key: StorageKey): T | null {
  if (typeof window === "undefined") return null;

  try {
    const item = localStorage.getItem(`${PREFIX}${key}`);
    return item ? (JSON.parse(item) as T) : null;
  } catch {
    return null;
  }
}

/**
 * Write a value to localStorage.
 */
export function setLocalStorage<T>(key: StorageKey, value: T): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value));
  } catch (error) {
    console.error(`[Storage] Failed to save to localStorage (${key}):`, error);
  }
}

/**
 * Remove a value from localStorage.
 */
export function removeLocalStorage(key: StorageKey): void {
  if (typeof window === "undefined") return;

  try {
    localStorage.removeItem(`${PREFIX}${key}`);
  } catch (error) {
    console.error(
      `[Storage] Failed to remove from localStorage (${key}):`,
      error,
    );
  }
}

/**
 * Clear all Poco-related localStorage entries.
 */
export function clearLocalStorage(): void {
  if (typeof window === "undefined") return;

  try {
    const keys = Object.keys(localStorage);
    keys.forEach((key) => {
      if (key.startsWith(PREFIX)) {
        localStorage.removeItem(key);
      }
    });
  } catch (error) {
    console.error("[Storage] Failed to clear localStorage:", error);
  }
}
