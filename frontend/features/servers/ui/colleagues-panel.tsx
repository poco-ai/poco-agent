"use client";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Hash, Plus, UserRound } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PersistentRuntimeBadge } from "@/components/shared/persistent-runtime-badge";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import {
  getUserAvatarUrl,
  getUserDisplayName,
} from "@/features/servers/lib/server-conversation-view";
import { getAgentRuntimeStatus } from "@/features/servers/lib/agent-runtime-status";
import type {
  ServerAgentItem,
  ServerMemberItem,
} from "@/features/servers/model/types";
import type { ColleagueSelection } from "@/features/servers/ui/server-workspace-types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { ServerAgentAvatar } from "@/features/servers/ui/server-agent-avatar";

export function ColleaguesPanel({
  agents,
  presets,
  members,
  selection,
  activeChannelIdByAgentId = {},
  canCreateAgent,
  canInviteMembers,
  onSelect,
  onOpenActiveChannel,
  onAddAgent,
  onInviteMember,
}: {
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerMemberItem[];
  selection: ColleagueSelection | null;
  activeChannelIdByAgentId?: Record<string, string>;
  canCreateAgent: boolean;
  canInviteMembers: boolean;
  onSelect: (selection: ColleagueSelection) => void;
  onOpenActiveChannel?: (channelId: string) => void;
  onAddAgent: () => void;
  onInviteMember: () => void;
}) {
  const { t } = useT("translation");
  return (
    <section className="flex min-h-0 min-w-0 w-full flex-1 flex-col border-r border-border bg-background">
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
        <section className="space-y-3">
          <div className="flex items-center justify-between gap-3 px-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("conversationView.colleagues.agents")} {agents.length}
            </p>
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onAddAgent}
              disabled={!canCreateAgent}
              aria-label={t("conversationView.agentPreset.title")}
              title={
                canCreateAgent
                  ? undefined
                  : t("conversationView.colleagues.createAgentPermissionHint")
              }
              className="size-8"
            >
              <Plus className="size-4" />
            </Button>
          </div>
          {!canCreateAgent ? (
            <p className="px-1 text-xs text-muted-foreground">
              {t("conversationView.colleagues.createAgentPermissionHint")}
            </p>
          ) : null}
          <div className="space-y-2">
            {agents.length > 0 ? (
              agents.map((agent) => (
                <button
                  key={agent.id}
                  type="button"
                  onClick={() => onSelect({ kind: "agent", id: agent.id })}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md border px-3 py-3 text-left transition-colors",
                    selection?.kind === "agent" && selection.id === agent.id
                      ? "border-primary/40 bg-primary/10"
                      : "border-transparent hover:bg-muted/20",
                  )}
                >
                  <ServerAgentAvatar
                    agent={agent}
                    presets={presets}
                    className="size-8 shrink-0"
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium text-foreground">
                      {agent.displayName}
                    </span>
                    <span className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                      <span>@{agent.handle}</span>
                      {(() => {
                        const runtimeStatus = getAgentRuntimeStatus(agent);
                        const activeChannelId =
                          activeChannelIdByAgentId[agent.id] ?? null;
                        return (
                          <>
                            <PersistentRuntimeBadge
                              status={runtimeStatus}
                              label={t(runtimeStatus.labelKey)}
                              pinnedLabel={t("runtime.labels.pinned")}
                              className="px-2 py-0.5"
                            />
                            {runtimeStatus.state === "running" &&
                            activeChannelId &&
                            onOpenActiveChannel ? (
                              <span
                                role="button"
                                tabIndex={0}
                                onClick={(event) => {
                                  event.stopPropagation();
                                  onOpenActiveChannel(activeChannelId);
                                }}
                                onKeyDown={(event) => {
                                  if (
                                    event.key === "Enter" ||
                                    event.key === " "
                                  ) {
                                    event.preventDefault();
                                    event.stopPropagation();
                                    onOpenActiveChannel(activeChannelId);
                                  }
                                }}
                                className="inline-flex items-center rounded-md px-1.5 py-0.5 text-foreground transition-colors hover:bg-muted/60"
                                title={t("conversationView.backToContext")}
                              >
                                <Hash className="size-3.5" />
                              </span>
                            ) : null}
                          </>
                        );
                      })()}
                    </span>
                  </span>
                </button>
              ))
            ) : (
              <div className="rounded-md border border-dashed border-border px-3 py-6 text-sm text-muted-foreground">
                {t("conversationView.colleagues.noAgents")}
              </div>
            )}
          </div>
        </section>

        <section className="mt-6 space-y-3">
          <div className="flex items-center justify-between gap-3 px-1">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
              {t("conversationView.colleagues.humans")} {members.length}
            </p>
            <Button
              type="button"
              variant="outline"
              size="icon"
              onClick={onInviteMember}
              disabled={!canInviteMembers}
              aria-label={t("conversationView.serverAccess.invitesTitle")}
              title={
                canInviteMembers
                  ? undefined
                  : t("conversationView.colleagues.invitePermissionHint")
              }
              className="size-8"
            >
              <Plus className="size-4" />
            </Button>
          </div>
          {!canInviteMembers ? (
            <p className="px-1 text-xs text-muted-foreground">
              {t("conversationView.colleagues.invitePermissionHint")}
            </p>
          ) : null}
          <div className="space-y-2">
            {members.length > 0 ? (
              members.map((member) => (
                <button
                  key={member.id}
                  type="button"
                  onClick={() => onSelect({ kind: "human", id: member.id })}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-md border px-3 py-3 text-left transition-colors",
                    selection?.kind === "human" && selection.id === member.id
                      ? "border-primary/40 bg-primary/10"
                      : "border-transparent hover:bg-muted/20",
                  )}
                >
                  {getUserAvatarUrl(member.user) ? (
                    <Avatar className="size-8 shrink-0 rounded-md border border-border">
                      <AvatarImage
                        src={getUserAvatarUrl(member.user) ?? undefined}
                        alt={getUserDisplayName(member.user, member.userId)}
                      />
                      <AvatarFallback className="rounded-md bg-muted text-xs font-semibold text-foreground">
                        {getUserDisplayName(member.user, member.userId)
                          .charAt(0)
                          .toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                  ) : (
                    <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                      <UserRound className="size-4" />
                    </span>
                  )}
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-foreground">
                      {getUserDisplayName(member.user, member.userId)}
                    </span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {member.role}
                    </span>
                  </span>
                </button>
              ))
            ) : (
              <div className="rounded-md border border-dashed border-border px-3 py-6 text-sm text-muted-foreground">
                {t("conversationView.colleagues.noHumans")}
              </div>
            )}
          </div>
        </section>
      </div>
    </section>
  );
}
