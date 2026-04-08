import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import {
  AUTH_SESSION_COOKIE_NAME,
  buildHomePath,
  buildLoginPath,
} from "@/features/auth";

export default async function Page({
  params,
}: {
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  const cookieStore = await cookies();

  if (cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value) {
    redirect(buildHomePath(lng));
  }

  redirect(buildLoginPath(lng, buildHomePath(lng)));
}
