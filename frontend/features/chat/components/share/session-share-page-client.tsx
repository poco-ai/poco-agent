"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  ArrowUp,
  GitFork,
  Loader2,
  LockKeyhole,
  MessageSquare,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PanelHeader } from "@/components/shared/panel-header";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Skeleton } from "@/components/ui/skeleton";
import { ChatMessageList } from "@/features/chat/components/chat/chat-message-list";
import { SessionShareExecutionPanel } from "@/features/chat/components/share/session-share-execution-panel";
import { sessionShareApi } from "@/features/chat/api/session-share-api";
import { parseMessages } from "@/features/chat/services/message-parser";
import type { SessionShareSnapshot } from "@/features/chat/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";

type ShareAuthStatus = "anonymous" | "authenticated" | "stale";

export function SessionSharePageClient({
  token,
  authStatus,
}: {
  token: string;
  authStatus: ShareAuthStatus;
}) {
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
  const canFork = authStatus === "authenticated";

  const handleFork = React.useCallback(async () => {
    if (!canFork || isForking) return;
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
  }, [canFork, isForking, lng, router, t, token]);
  const showExecutionPanel = Boolean(snapshot && snapshot.runs.length > 0);

  return (
    <div className="flex h-dvh min-h-0 min-w-0 overflow-hidden bg-background text-foreground select-text">
      <ResizablePanelGroup
        key={showExecutionPanel ? "share-with-execution" : "share-transcript"}
        direction="horizontal"
        className="min-h-0 min-w-0"
      >
        <ResizablePanel
          defaultSize={showExecutionPanel ? 45 : 100}
          minSize={35}
          className="min-h-0 min-w-0 overflow-hidden"
        >
          <div className="flex h-full min-h-0 min-w-0 flex-col bg-background">
            <PanelHeader
              icon={MessageSquare}
              title={snapshot?.session.title || t("chat.sharedConversation")}
              description={
                snapshot
                  ? t("chat.shareSourceStatus", {
                      status: snapshot.session.status,
                    })
                  : t("chat.shareLoading")
              }
              action={
                <div className="flex min-w-0 items-center gap-2">
                  <Badge variant="secondary" className="h-8 shrink-0 gap-1.5">
                    <LockKeyhole className="size-3" />
                    {t("chat.readonly")}
                  </Badge>
                  {canFork ? (
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
                  ) : null}
                </div>
              }
            />

            <div className="min-h-0 flex-1 overflow-hidden">
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
                  showUserPromptTimeline
                  contentPaddingClassName="px-6 md:px-10 lg:px-12"
                />
              ) : (
                <div className="px-6 py-10 text-sm text-muted-foreground">
                  {t("chat.shareNotFound")}
                </div>
              )}
            </div>

            <div className="shrink-0 border-t border-border px-4 py-3">
              <div className="flex min-h-11 items-center gap-3 rounded-xl border border-border bg-muted/30 px-4 text-sm text-muted-foreground">
                <span className="min-w-0 flex-1 truncate">
                  {t("chat.shareReadonlyComposerPlaceholder")}
                </span>
                <Button
                  type="button"
                  size="icon"
                  variant="secondary"
                  disabled
                  aria-label={t("chat.readonly")}
                  className="size-8 shrink-0"
                >
                  <ArrowUp className="size-4" />
                </Button>
              </div>
            </div>
          </div>
        </ResizablePanel>

        {showExecutionPanel && snapshot ? (
          <div className="hidden min-h-0 min-w-0 lg:contents">
            <ResizableHandle withHandle />
            <ResizablePanel
              defaultSize={55}
              minSize={30}
              className="min-h-0 min-w-0 overflow-hidden"
            >
              <SessionShareExecutionPanel snapshot={snapshot} />
            </ResizablePanel>
          </div>
        ) : null}
      </ResizablePanelGroup>
    </div>
  );
}
