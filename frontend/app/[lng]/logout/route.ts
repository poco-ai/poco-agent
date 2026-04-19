import { NextRequest, NextResponse } from "next/server";

import {
  AUTH_SESSION_COOKIE_NAME,
  buildHomePath,
  buildLoginPath,
  normalizeNextPath,
} from "@/features/auth";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";

function getFrontendPublicUrl(): string | null {
  const value = (
    process.env.FRONTEND_PUBLIC_URL ||
    process.env.NEXT_PUBLIC_FRONTEND_PUBLIC_URL ||
    ""
  ).trim();
  return value || null;
}

function buildRedirectUrl(path: string, request: NextRequest): URL {
  const frontendPublicUrl = getFrontendPublicUrl();
  if (frontendPublicUrl) {
    return new URL(path, frontendPublicUrl);
  }

  return new URL(path, request.url);
}

async function revokeServerSession(): Promise<void> {
  try {
    await apiClient.post(API_ENDPOINTS.authLogout, undefined, {
      cache: "no-store",
    });
  } catch {
    // Clearing the local session cookie is the primary concern here.
  }
}

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ lng: string }> },
) {
  const { lng } = await context.params;
  const requestedNextPath = request.nextUrl.searchParams.get("next");
  const nextPath = normalizeNextPath(
    requestedNextPath ?? buildLoginPath(lng, buildHomePath(lng)),
    lng,
  );

  await revokeServerSession();

  const response = NextResponse.redirect(buildRedirectUrl(nextPath, request));
  response.cookies.set({
    name: AUTH_SESSION_COOKIE_NAME,
    value: "",
    expires: new Date(0),
    maxAge: 0,
    httpOnly: true,
    path: "/",
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
  });
  return response;
}
