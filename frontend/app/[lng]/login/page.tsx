import { redirect } from "next/navigation";

import {
  LoginPageClient,
  buildSessionRecoveryPath,
  normalizeNextPath,
} from "@/features/auth";
import { getServerAuthState } from "@/features/auth/lib/server-session";

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
  const authState = await getServerAuthState();

  if (authState.status === "authenticated") {
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
      providers={authState.config.providers}
    />
  );
}
