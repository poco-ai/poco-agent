"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, GitFork, Loader2, LockKeyhole } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessageList } from "@/features/chat/components/chat/chat-message-list";
import { ConversationTimelineRail } from "@/features/chat/components/shared/conversation-timeline-rail";
import { sessionShareApi } from "@/features/chat/api/session-share-api";
import { parseMessages } from "@/features/chat/services/message-parser";
import type { SessionShareSnapshot } from "@/features/chat/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";

export function SessionSharePageClient({ token }: { token: string }) {
  const router = useRouter();
  const lng = useLanguage();
  const { t } = useT("translation");
  const [snapshot, setSnapshot] = React.useState<SessionShareSnapshot | null>(
    null,
  );
  const [isLoading, setIsLoading] = React.useState(true);
  const [isForking, setIsForking] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    void sessionShareApi
      .getSnapshot(token)
      .then((result) => {
        if (!cancelled) {
          setSnapshot(result);
        }
      })
      .catch((error) => {
        console.error("[SessionSharePage] load share failed", error);
        if (!cancelled) {
          toast.error(t("chat.shareLoadFailed"));
          setSnapshot(null);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [t, token]);

  const parsedMessages = React.useMemo(() => {
    if (!snapshot) return [];
    return parseMessages(
      snapshot.messages,
      snapshot.runs.map((run) => run.userMessageId),
    ).messages;
  }, [snapshot]);

  const handleFork = React.useCallback(async () => {
    if (isForking) return;
    setIsForking(true);
    try {
      const forked = await sessionShareApi.forkShare(token);
      toast.success(t("chat.shareForkCreated"));
      router.push(
        lng ? `/${lng}/chat/${forked.sessionId}` : `/chat/${forked.sessionId}`,
      );
    } catch (error) {
      console.error("[SessionSharePage] fork share failed", error);
      toast.error(t("chat.shareForkFailed"));
    } finally {
      setIsForking(false);
    }
  }, [isForking, lng, router, t, token]);

  return (
    <main className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="flex min-h-16 items-center justify-between gap-4 border-b border-border px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={() => router.push(lng ? `/${lng}` : "/")}
            aria-label={t("common.back")}
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <h1 className="truncate text-base font-semibold sm:text-lg">
                {snapshot?.session.title || t("chat.sharedConversation")}
              </h1>
              <Badge variant="secondary" className="shrink-0">
                <LockKeyhole className="size-3" />
                {t("chat.readonly")}
              </Badge>
            </div>
            <p className="truncate text-xs text-muted-foreground">
              {snapshot
                ? t("chat.shareSourceStatus", {
                    status: snapshot.session.status,
                  })
                : t("chat.shareLoading")}
            </p>
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => void handleFork()}
          disabled={!snapshot || isForking}
        >
          {isForking ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <GitFork className="size-4" />
          )}
          {t("chat.forkToMyChats")}
        </Button>
      </header>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <section className="min-w-0 flex-1 overflow-hidden">
          {isLoading ? (
            <div className="space-y-4 px-6 py-6">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-24 rounded-md" />
              ))}
            </div>
          ) : snapshot ? (
            <ChatMessageList
              messages={parsedMessages}
              sessionStatus={snapshot.session.status}
              showUserPromptTimeline={false}
            />
          ) : (
            <div className="px-6 py-10 text-sm text-muted-foreground">
              {t("chat.shareNotFound")}
            </div>
          )}
        </section>
        <ConversationTimelineRail
          title={t("chat.timeline")}
          emptyLabel={t("chat.timelineEmpty")}
          items={snapshot?.timeline ?? []}
          className="hidden lg:flex"
        />
      </div>
    </main>
  );
}
