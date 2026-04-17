import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { AUTH_SESSION_COOKIE_NAME } from "@/features/auth/lib/paths";
import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";

export type AuthProvider = "google" | "github";

export interface ServerAuthConfig {
  mode: "oauth_required" | "oauth_optional" | "single_user";
  login_required: boolean;
  single_user_effective: boolean;
  setup_required: boolean;
  configured_providers: AuthProvider[];
  providers: Array<{
    name: AuthProvider;
    enabled: boolean;
  }>;
}

export type ServerAuthState =
  | { status: "anonymous" }
  | { status: "authenticated" }
  | { status: "stale" }
  | { status: "single_user" };

export const getServerAuthConfig = cache(
  async (): Promise<ServerAuthConfig> => {
    return apiClient.get<ServerAuthConfig>(API_ENDPOINTS.authConfig, {
      cache: "no-store",
    });
  },
);

export const getServerAuthState = cache(async (): Promise<ServerAuthState> => {
  const authConfig = await getServerAuthConfig();
  if (authConfig.single_user_effective) {
    return { status: "single_user" };
  }

  const cookieStore = await cookies();
  if (!cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value) {
    return { status: "anonymous" };
  }

  try {
    await apiClient.get<unknown>(API_ENDPOINTS.authMe, {
      cache: "no-store",
    });
    return { status: "authenticated" };
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 401) {
      return { status: "stale" };
    }
    throw error;
  }
});
