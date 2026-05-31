"use client";

import type { LucideIcon } from "lucide-react";
import {
  Hash,
  Inbox,
  LayoutGrid,
  MessageSquare,
  Plus,
  Search,
  Server as ServerIcon,
  Users,
} from "lucide-react";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  ServerChannelItem,
  ServerItem,
} from "@/features/servers/model/types";
import type { WorkspaceMode } from "@/features/servers/ui/server-workspace-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  ["searchInServer", Search, "search"],
  ["tasksTab", LayoutGrid, "tasks"],
  ["colleaguesTab", Users, "colleagues"],
  ["inbox", Inbox, "inbox"],
] as const satisfies readonly [string, LucideIcon, WorkspaceMode][];

export function ServerWorkspaceSidebar({
  servers,
  selectedServerId,
  mode,
  inboxCount,
  topLevelChannels,
  directMessages,
  activeChannelId,
  onSelectServer,
  onOpenServerAccess,
  onOpenMode,
  onOpenTasks,
  onOpenChannel,
  onCreateChannel,
  variant = "desktop",
}: {
  servers: ServerItem[];
  selectedServerId: string | null;
  mode: WorkspaceMode;
  inboxCount: number;
  topLevelChannels: ServerChannelItem[];
  directMessages: ServerChannelItem[];
  activeChannelId: string | null;
  onSelectServer: (serverId: string) => void;
  onOpenServerAccess: () => void;
  onOpenMode: (mode: WorkspaceMode) => void;
  onOpenTasks: () => void;
  onOpenChannel: (channel: ServerChannelItem) => void;
  onCreateChannel: () => void;
  variant?: "desktop" | "mobile";
}) {
  const { t } = useT("translation");
  const isMobileVariant = variant === "mobile";
  const selectedServer =
    servers.find((server) => server.id === selectedServerId) ?? null;

  return (
    <aside
      className={cn(
        "shrink-0 border-border bg-card",
        isMobileVariant
          ? "flex h-full w-full flex-col"
          : "hidden w-[17rem] border-r md:flex md:flex-col lg:w-[18rem]",
      )}
    >
      {isMobileVariant ? (
        <PageHeaderShell
          className="bg-card"
          left={
            <div className="flex min-w-0 items-center gap-3">
              <ServerIcon
                className="hidden size-5 text-muted-foreground md:block"
                aria-hidden="true"
              />
              <div className="min-w-0">
                <p className="text-base font-semibold leading-tight">
                  {t("servers.title")}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {selectedServer
                    ? t("servers.currentServer", {
                        name: selectedServer.name,
                      })
                    : t("servers.noServer")}
                </p>
              </div>
            </div>
          }
        />
      ) : null}
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-2">
          <div className="min-w-0 flex-1">
            <Select
              value={selectedServerId ?? ""}
              onValueChange={onSelectServer}
            >
              <SelectTrigger className="w-full min-w-0 border-border bg-background text-sm">
                <SelectValue placeholder={t("servers.title")} />
              </SelectTrigger>
              <SelectContent>
                {servers.map((server) => (
                  <SelectItem key={server.id} value={server.id}>
                    {server.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={onOpenServerAccess}
            aria-label={t("conversationView.serverAccess.title")}
            className="size-9 shrink-0"
          >
            <Plus className="size-4" />
          </Button>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 py-4">
        <div className="space-y-1">
          {NAV_ITEMS.map(([key, Icon, nextMode]) => {
            const isActive = mode === nextMode;
            return (
              <button
                key={nextMode}
                type="button"
                onClick={() => {
                  if (nextMode === "tasks") {
                    onOpenTasks();
                    return;
                  }
                  onOpenMode(nextMode);
                }}
                className={cn(
                  "flex w-full items-center justify-between rounded-md px-3 py-2.5 text-left transition-colors",
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-foreground hover:bg-muted/20",
                )}
              >
                <span className="flex items-center gap-3 text-sm">
                  <Icon className="size-5" />
                  {t(`conversationView.${key}`)}
                </span>
                {nextMode === "inbox" ? (
                  <span className="text-sm text-muted-foreground">
                    {inboxCount}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>

        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("conversationView.channels")}
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onCreateChannel}
              aria-label={t("conversationView.createChannel.title")}
            >
              +
            </Button>
          </div>
          <div className="space-y-2">
            {topLevelChannels.map((channel) => (
              <button
                key={channel.id}
                type="button"
                onClick={() => onOpenChannel(channel)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md border px-4 py-3 text-left transition-colors",
                  channel.id === activeChannelId
                    ? "border-primary/40 bg-primary/10 text-foreground"
                    : "border-transparent bg-transparent text-foreground hover:bg-muted/20",
                )}
              >
                <Hash className="size-3" />
                <span className="truncate text-sm">{channel.name}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("conversationView.directMessages")}
            </p>
            <span className="text-xs text-muted-foreground">
              {directMessages.length}
            </span>
          </div>
          <div className="space-y-2">
            {directMessages.map((channel) => (
              <button
                key={channel.id}
                type="button"
                onClick={() => onOpenChannel(channel)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-md border px-4 py-3 text-left transition-colors",
                  channel.id === activeChannelId
                    ? "border-primary/40 bg-primary/10 text-foreground"
                    : "border-transparent bg-transparent text-foreground hover:bg-muted/20",
                )}
              >
                <MessageSquare className="size-3" />
                <span className="truncate text-sm">{channel.name}</span>
              </button>
            ))}
          </div>
        </section>
      </div>
    </aside>
  );
}
