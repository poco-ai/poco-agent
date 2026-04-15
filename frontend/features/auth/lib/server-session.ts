import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";
import {
  AUTH_SESSION_COOKIE_NAME,
  type AuthProvider,
} from "@/features/auth/lib/paths";

export interface AuthConfig {
  auth_mode: "disabled" | "oauth_required";
  login_required: boolean;
  providers: AuthProvider[];
  workspace_features_enabled: boolean;
}

export type ServerAuthState =
  | { status: "anonymous"; config: AuthConfig }
  | { status: "authenticated"; config: AuthConfig }
  | { status: "stale"; config: AuthConfig };

export const getServerAuthState = cache(async (): Promise<ServerAuthState> => {
  const config = await apiClient.get<AuthConfig>(API_ENDPOINTS.authConfig, {
    cache: "no-store",
  });

  if (!config.login_required) {
    return { status: "authenticated", config };
  }

  const cookieStore = await cookies();
  if (!cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value) {
    return { status: "anonymous", config };
  }

  try {
    await apiClient.get<unknown>(API_ENDPOINTS.authMe, {
      cache: "no-store",
    });
    return { status: "authenticated", config };
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 401) {
      return { status: "stale", config };
    }
    throw error;
  }
});
