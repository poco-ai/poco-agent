"use client";

import * as React from "react";
import { Compass } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import type { UserInputRequest } from "@/features/chat/types";

export function EnterPlanModeCard({
  request,
  isSubmitting = false,
  onConfirm,
}: {
  request: UserInputRequest;
  isSubmitting?: boolean;
  onConfirm: () => Promise<void>;
}) {
  const { t } = useT("translation");

  const [secondsLeft, setSecondsLeft] = React.useState<number | null>(null);

  React.useEffect(() => {
    if (!request.expires_at) {
      setSecondsLeft(null);
      return;
    }
    const expiresAt = new Date(request.expires_at).getTime();
    const update = () => {
      const now = Date.now();
      const diff = Math.max(0, Math.ceil((expiresAt - now) / 1000));
      setSecondsLeft(diff);
    };
    update();
    const timer = window.setInterval(update, 1000);
    return () => window.clearInterval(timer);
  }, [request.expires_at]);

  if (secondsLeft === 0) {
    return null;
  }

  return (
    <div className="border border-primary/30 rounded-lg bg-gradient-to-br from-primary/5 to-primary/10 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-primary shrink-0">
            <Compass className="size-4" />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-medium text-foreground">
              {t("chat.enterPlanModeTitle")}
            </div>
            <div className="text-xs text-muted-foreground">
              {t("chat.enterPlanModeHint")}
            </div>
          </div>
        </div>

        {secondsLeft !== null && (
          <div
            className={cn(
              "text-xs shrink-0",
              secondsLeft <= 10 ? "text-destructive" : "text-muted-foreground",
            )}
          >
            {t("chat.askUserTimeout", { seconds: secondsLeft })}
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2">
        <Button type="button" disabled={isSubmitting} onClick={onConfirm}>
          {t("chat.enterPlanModeConfirm")}
        </Button>
      </div>
    </div>
  );
}
