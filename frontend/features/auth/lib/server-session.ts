import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";
import { AUTH_SESSION_COOKIE_NAME } from "@/features/auth/lib/paths";

export type ServerAuthState =
  | { status: "anonymous" }
  | { status: "authenticated" }
  | { status: "stale" };

export const getServerAuthState = cache(async (): Promise<ServerAuthState> => {
  const cookieStore = await cookies();
  // The backend can authenticate cookieless requests in single-user and
  // disabled auth modes, so always probe /auth/me and only use cookie
  // presence to distinguish "anonymous" from "stale" on 401.
  const hasSessionCookie = Boolean(
    cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value,
  );

  try {
    await apiClient.get<unknown>(API_ENDPOINTS.authMe, {
      cache: "no-store",
    });
    return { status: "authenticated" };
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 401) {
      return { status: hasSessionCookie ? "stale" : "anonymous" };
    }
    throw error;
  }
});
