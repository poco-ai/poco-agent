/**
 * SessionStorage wrapper with type safety and error handling.
 */
const PREFIX = "poco_";

export type SessionStorageKey =
  | "temp_state"
  | "navigation_state"
  | "filter_state";

/**
 * Read a value from sessionStorage.
 */
export function getSessionStorage<T>(key: SessionStorageKey): T | null {
  if (typeof window === "undefined") return null;

  try {
    const item = sessionStorage.getItem(`${PREFIX}${key}`);
    return item ? (JSON.parse(item) as T) : null;
  } catch {
    return null;
  }
}

/**
 * Write a value to sessionStorage.
 */
export function setSessionStorage<T>(key: SessionStorageKey, value: T): void {
  if (typeof window === "undefined") return;

  try {
    sessionStorage.setItem(`${PREFIX}${key}`, JSON.stringify(value));
  } catch (error) {
    console.error(
      `[Storage] Failed to save to sessionStorage (${key}):`,
      error,
    );
  }
}

/**
 * Remove a value from sessionStorage.
 */
export function removeSessionStorage(key: SessionStorageKey): void {
  if (typeof window === "undefined") return;

  try {
    sessionStorage.removeItem(`${PREFIX}${key}`);
  } catch (error) {
    console.error(
      `[Storage] Failed to remove from sessionStorage (${key}):`,
      error,
    );
  }
}
