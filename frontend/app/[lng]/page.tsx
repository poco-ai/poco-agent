import { redirect } from "next/navigation";

import {
  buildHomePath,
  buildLoginPath,
  buildSessionRecoveryPath,
} from "@/features/auth";
import {
  getServerAuthConfig,
  getServerAuthState,
} from "@/features/auth/lib/server-session";

export default async function Page({
  params,
}: {
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  const authConfig = await getServerAuthConfig();
  const authState = await getServerAuthState();

  if (
    authState.status === "authenticated" ||
    authState.status === "single_user"
  ) {
    redirect(buildHomePath(lng));
  }
  if (authState.status === "stale") {
    redirect(buildSessionRecoveryPath(lng, buildHomePath(lng)));
  }
  if (!authConfig.login_required) {
    redirect(buildHomePath(lng));
  }

  redirect(buildLoginPath(lng, buildHomePath(lng)));
}
