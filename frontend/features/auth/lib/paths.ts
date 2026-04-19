import type { AuthProvider } from "@/features/auth/model/types";

export const AUTH_SESSION_COOKIE_NAME =
  process.env.NEXT_PUBLIC_AUTH_COOKIE_NAME || "poco_session";

export function buildHomePath(lng: string): string {
  return `/${lng}/home`;
}

export function normalizeNextPath(
  nextPath: string | null | undefined,
  lng: string,
): string {
  if (!nextPath) return buildHomePath(lng);
  const value = nextPath.trim();
  if (!value || value.startsWith("//")) return buildHomePath(lng);
  return value.startsWith("/") ? value : buildHomePath(lng);
}

export function buildLoginPath(lng: string, nextPath?: string): string {
  const normalizedNext = normalizeNextPath(nextPath, lng);
  const search = new URLSearchParams({ next: normalizedNext });
  return `/${lng}/login?${search.toString()}`;
}

export function buildLogoutPath(lng: string, nextPath?: string): string {
  const normalizedNext = normalizeNextPath(nextPath, lng);
  const search = new URLSearchParams({ next: normalizedNext });
  return `/${lng}/logout?${search.toString()}`;
}

export function buildSessionRecoveryPath(
  lng: string,
  nextPath?: string,
): string {
  return buildLogoutPath(lng, buildLoginPath(lng, nextPath));
}

export function buildProviderLoginPath(
  provider: AuthProvider,
  nextPath: string,
): string {
  const search = new URLSearchParams({ next: nextPath });
  return `/api/v1/auth/${provider}/login?${search.toString()}`;
}
