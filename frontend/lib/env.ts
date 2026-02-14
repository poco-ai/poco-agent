const DEFAULT_SESSION_POLLING_INTERVAL_MS = 6000;

export const isDev = process.env.NODE_ENV !== "production";

function parsePositiveInt(value: string | undefined): number | null {
  if (!value) return null;
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed) || parsed <= 0) return null;
  return parsed;
}

export function getSessionPollingIntervalMs(): number {
  const parsed = parsePositiveInt(
    process.env.NEXT_PUBLIC_SESSION_POLLING_INTERVAL,
  );
  return parsed ?? DEFAULT_SESSION_POLLING_INTERVAL_MS;
}
