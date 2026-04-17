import { redirect } from "next/navigation";

import {
  LoginPageClient,
  buildSessionRecoveryPath,
  normalizeNextPath,
} from "@/features/auth";
import {
  getServerAuthConfig,
  getServerAuthState,
} from "@/features/auth/lib/server-session";

export default async function LoginPage({
  params,
  searchParams,
}: {
  params: Promise<{ lng: string }>;
  searchParams: Promise<{ next?: string; error?: string }>;
}) {
  const { lng } = await params;
  const { next, error } = await searchParams;
  const nextPath = normalizeNextPath(next, lng);
  const authConfig = await getServerAuthConfig();
  const authState = await getServerAuthState();

  if (
    authState.status === "authenticated" ||
    authState.status === "single_user"
  ) {
    redirect(nextPath);
  }
  if (authState.status === "stale") {
    redirect(buildSessionRecoveryPath(lng, nextPath));
  }

  return (
    <LoginPageClient
      lng={lng}
      nextPath={nextPath}
      errorCode={error}
      configuredProviders={authConfig.configured_providers}
      setupRequired={authConfig.setup_required}
    />
  );
}
