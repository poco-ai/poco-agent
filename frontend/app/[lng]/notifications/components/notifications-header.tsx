"use client";

import { ArrowLeft, BellRing } from "lucide-react";
import { useRouter } from "next/navigation";

import { useT } from "@/app/i18n/client";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";

export function NotificationsHeader() {
  const { t } = useT("translation");
  const router = useRouter();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-border/50 bg-background/50 px-6 backdrop-blur-sm sticky top-0 z-10">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
          className="mr-2"
        >
          <ArrowLeft className="size-5" />
        </Button>
        <div className="flex items-center justify-center p-2 rounded-lg bg-primary/10">
          <BellRing className="size-5 text-primary" />
        </div>
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold tracking-tight">
            {t("notifications.title")}
          </span>
          <Separator orientation="vertical" className="h-4" />
          <span className="text-sm text-muted-foreground">
            {t("notifications.subtitle")}
          </span>
        </div>
      </div>
    </header>
  );
}
