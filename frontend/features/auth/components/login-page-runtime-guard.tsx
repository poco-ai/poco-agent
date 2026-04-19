"use client";

import * as React from "react";
import { useRouter } from "next/navigation";

import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";
import type { AuthProvider } from "@/features/auth/model/types";

interface AuthConfigResponse {
  mode: "oauth_required" | "oauth_optional" | "single_user";
  login_required: boolean;
  single_user_effective: boolean;
  setup_required: boolean;
  configured_providers: AuthProvider[];
}

interface LoginPageRuntimeGuardProps {
  nextPath: string;
  onResolved: (value: {
    configuredProviders: AuthProvider[];
    setupRequired: boolean;
  }) => void;
  onError: (message: string) => void;
}

const AUTH_CONFIG_CACHE_TTL_MS = 30_000;

let authConfigCache: {
  expiresAt: number;
  value: AuthConfigResponse;
} | null = null;

async function fetchAuthConfig(): Promise<AuthConfigResponse> {
  const now = Date.now();
  if (authConfigCache && authConfigCache.expiresAt > now) {
    return authConfigCache.value;
  }

  const value = await apiClient.get<AuthConfigResponse>(
    API_ENDPOINTS.authConfig,
    {
      cache: "no-store",
    },
  );
  authConfigCache = {
    value,
    expiresAt: now + AUTH_CONFIG_CACHE_TTL_MS,
  };
  return value;
}

export function LoginPageRuntimeGuard({
  nextPath,
  onResolved,
  onError,
}: LoginPageRuntimeGuardProps) {
  const router = useRouter();

  React.useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        const authConfig = await fetchAuthConfig();
        if (cancelled) return;

        if (authConfig.single_user_effective) {
          router.replace(nextPath);
          return;
        }

        onResolved({
          configuredProviders: authConfig.configured_providers,
          setupRequired: authConfig.setup_required,
        });
      } catch (error) {
        if (cancelled) return;

        if (error instanceof ApiError && error.statusCode >= 500) {
          onResolved({
            configuredProviders: [],
            setupRequired: true,
          });
          return;
        }

        onError("runtime_config_failed");
      }
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, [nextPath, onError, onResolved, router]);

  return null;
}
