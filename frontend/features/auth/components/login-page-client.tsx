"use client";

import { AlertCircle } from "lucide-react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/client";
import {
  type AuthProvider,
  buildProviderLoginPath,
  normalizeNextPath,
} from "@/features/auth/lib/paths";

interface LoginPageClientProps {
  lng: string;
  nextPath?: string | null;
  errorCode?: string | null;
  providers: AuthProvider[];
}

function GithubIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5 fill-current">
      <path d="M12 1.5a10.5 10.5 0 0 0-3.32 20.46c.52.1.71-.22.71-.5v-1.73c-2.88.63-3.49-1.21-3.49-1.21-.47-1.2-1.16-1.52-1.16-1.52-.95-.64.07-.63.07-.63 1.05.07 1.6 1.07 1.6 1.07.94 1.6 2.46 1.14 3.06.87.1-.68.37-1.14.66-1.4-2.3-.26-4.73-1.15-4.73-5.14 0-1.14.41-2.06 1.08-2.79-.11-.27-.47-1.35.1-2.81 0 0 .88-.28 2.89 1.06A10 10 0 0 1 12 6.57c.89 0 1.79.12 2.63.35 2-.34 2.88-1.06 2.88-1.06.57 1.46.22 2.54.11 2.81.67.73 1.08 1.65 1.08 2.79 0 4-2.43 4.87-4.75 5.12.37.32.7.95.7 1.92v2.85c0 .28.19.6.72.5A10.5 10.5 0 0 0 12 1.5Z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="size-5">
      <path
        fill="#4285F4"
        d="M21.6 12.23c0-.72-.06-1.25-.2-1.8H12v3.39h5.52c-.1.84-.64 2.11-1.84 2.96l-.02.11 2.68 2.08.19.02c1.74-1.61 2.87-3.98 2.87-6.76Z"
      />
      <path
        fill="#34A853"
        d="M12 22c2.7 0 4.96-.89 6.61-2.41l-3.15-2.44c-.84.58-1.97.99-3.46.99-2.64 0-4.88-1.74-5.68-4.14l-.1.01-2.79 2.16-.03.09A9.99 9.99 0 0 0 12 22Z"
      />
      <path
        fill="#FBBC05"
        d="M6.32 14c-.21-.62-.33-1.28-.33-1.97s.12-1.35.32-1.97l-.01-.13-2.82-2.19-.09.04A9.94 9.94 0 0 0 2 12.03c0 1.61.38 3.13 1.05 4.47L6.32 14Z"
      />
      <path
        fill="#EA4335"
        d="M12 5.86c1.88 0 3.14.81 3.87 1.49l2.83-2.76C16.95 2.98 14.7 2 12 2a9.99 9.99 0 0 0-8.61 4.76L6.3 8.99c.81-2.4 3.05-4.13 5.7-4.13Z"
      />
    </svg>
  );
}

export function LoginPageClient({
  lng,
  nextPath,
  errorCode,
  providers,
}: LoginPageClientProps) {
  const { t } = useT("translation");
  const targetPath = normalizeNextPath(nextPath, lng);

  const errorMessage =
    errorCode && errorCode !== ""
      ? t(`auth.login.errors.${errorCode}`, {
          defaultValue: t("auth.login.errors.default"),
        })
      : null;

  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-4 py-10">
      <Card className="w-full max-w-md border-border/60 bg-card/95 shadow-lg">
        <CardHeader className="space-y-3 text-center">
          <CardTitle className="text-2xl font-semibold text-foreground">
            {t("auth.login.title")}
          </CardTitle>
          <CardDescription className="text-sm text-muted-foreground">
            {t("auth.login.subtitle")}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 pb-6">
          {errorMessage ? (
            <div className="flex items-start gap-3 rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          ) : null}

          <div className="grid gap-3">
            {providers.includes("google") ? (
              <Button asChild size="lg" className="w-full gap-2">
                <a href={buildProviderLoginPath("google", targetPath)}>
                  <GoogleIcon />
                  <span>{t("auth.login.google")}</span>
                </a>
              </Button>
            ) : null}

            {providers.includes("github") ? (
              <Button
                asChild
                size="lg"
                variant="outline"
                className="w-full gap-2"
              >
                <a href={buildProviderLoginPath("github", targetPath)}>
                  <GithubIcon />
                  <span>{t("auth.login.github")}</span>
                </a>
              </Button>
            ) : null}
          </div>

          <p className="text-center text-xs leading-5 text-muted-foreground">
            {providers.length > 0
              ? t("auth.login.hint")
              : t("auth.login.noProviders")}
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
