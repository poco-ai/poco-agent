"use client";

import * as React from "react";
import {
  Activity,
  Building2,
  Copy,
  RefreshCw,
  Shield,
  Ticket,
  Users,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyMedia,
  EmptyTitle,
} from "@/components/ui/empty";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { workspacesApi } from "@/features/workspaces/api/workspaces-api";
import {
  formatActivityAction,
  formatWorkspaceKind,
  formatWorkspaceRole,
} from "@/features/workspaces/lib/format";
import { useWorkspaceContext } from "@/features/workspaces/model/workspace-context";
import type {
  ActivityLog,
  WorkspaceInvite,
  WorkspaceMember,
  WorkspaceRole,
} from "@/features/workspaces/model/types";
import { TeamShell } from "@/features/workspaces/ui/team-shell";

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

function WorkspaceSummaryCards({
  members,
  invites,
}: {
  members: WorkspaceMember[];
  invites: WorkspaceInvite[];
}) {
  const { t } = useT("translation");
  const { currentWorkspace } = useWorkspaceContext();
  const activeInvites = invites.filter((invite) => invite.revokedAt === null);

  const cards = [
    {
      icon: Building2,
      label: t("workspaces.summary.kind"),
      value: currentWorkspace
        ? formatWorkspaceKind(t, currentWorkspace.kind)
        : t("workspaces.emptyValue"),
    },
    {
      icon: Users,
      label: t("workspaces.summary.members"),
      value: String(members.length),
    },
    {
      icon: Ticket,
      label: t("workspaces.summary.invites"),
      value: String(activeInvites.length),
    },
  ];

  return (
    <div className="grid gap-3 md:grid-cols-3">
      {cards.map(({ icon: Icon, label, value }) => (
        <Card key={label} className="overflow-hidden border-border/60">
          <CardContent className="flex items-center gap-4 p-5">
            <div className="rounded-xl bg-primary/10 p-3 text-primary">
              <Icon className="size-5" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground">{label}</p>
              <p className="text-2xl font-semibold">{value}</p>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

export function TeamPageClient() {
  const { t } = useT("translation");
  const { currentWorkspace, isLoading } = useWorkspaceContext();
  const [members, setMembers] = React.useState<WorkspaceMember[]>([]);
  const [invites, setInvites] = React.useState<WorkspaceInvite[]>([]);
  const [activity, setActivity] = React.useState<ActivityLog[]>([]);
  const [isRefreshing, setIsRefreshing] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) return;
    setIsRefreshing(true);
    try {
      const [nextMembers, nextInvites, nextActivity] = await Promise.all([
        workspacesApi.listMembers(currentWorkspace.id),
        workspacesApi.listInvites(currentWorkspace.id),
        workspacesApi.listActivity(currentWorkspace.id),
      ]);
      setMembers(nextMembers);
      setInvites(nextInvites);
      setActivity(nextActivity);
    } catch (error) {
      console.error("[Workspaces] overview refresh failed", error);
      toast.error(t("workspaces.toasts.loadFailed"));
    } finally {
      setIsRefreshing(false);
    }
  }, [currentWorkspace, t]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <TeamShell
      activePage="overview"
      title={t("workspaces.pages.overview.title")}
      subtitle={t("workspaces.currentWorkspace", {
        name: currentWorkspace?.name ?? t("workspaces.noWorkspace"),
      })}
    >
      {isLoading ? (
        <Skeleton className="h-40 rounded-2xl" />
      ) : (
        <>
          <WorkspaceSummaryCards members={members} invites={invites} />
          <Card className="border-border/60">
            <CardHeader className="gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="space-y-1">
                <CardTitle>{t("workspaces.activity.title")}</CardTitle>
                <CardDescription>
                  {t("workspaces.activity.description")}
                </CardDescription>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => void refresh()}
                disabled={isRefreshing}
              >
                <RefreshCw
                  className={cn("size-4", isRefreshing && "animate-spin")}
                />
                {t("workspaces.refresh")}
              </Button>
            </CardHeader>
            <CardContent className="space-y-3 pb-6">
              {activity.length === 0 ? (
                <Empty className="min-h-56 rounded-2xl border border-dashed border-border/70 bg-muted/10">
                  <EmptyContent>
                    <EmptyMedia variant="icon">
                      <Activity className="size-5" />
                    </EmptyMedia>
                    <EmptyHeader>
                      <EmptyTitle>{t("workspaces.activity.title")}</EmptyTitle>
                      <EmptyDescription>
                        {t("workspaces.activity.empty")}
                      </EmptyDescription>
                    </EmptyHeader>
                  </EmptyContent>
                </Empty>
              ) : (
                activity.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-start gap-3 rounded-2xl border border-border/60 bg-muted/15 p-4"
                  >
                    <Activity className="mt-0.5 size-4 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {formatActivityAction(t, item.action)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatDateTime(item.createdAt)}
                      </p>
                    </div>
                    <Badge variant="outline">{item.targetType}</Badge>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </TeamShell>
  );
}

export function TeamMembersPageClient() {
  const { t } = useT("translation");
  const { currentWorkspace } = useWorkspaceContext();
  const [members, setMembers] = React.useState<WorkspaceMember[]>([]);
  const [isLoading, setIsLoading] = React.useState(true);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) return;
    setIsLoading(true);
    try {
      setMembers(await workspacesApi.listMembers(currentWorkspace.id));
    } catch (error) {
      console.error("[Workspaces] members refresh failed", error);
      toast.error(t("workspaces.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkspace, t]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <TeamShell
      activePage="members"
      title={t("workspaces.pages.members.title")}
      subtitle={t("workspaces.members.description")}
    >
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle>{t("workspaces.members.title")}</CardTitle>
          <CardDescription>{t("workspaces.members.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pb-6">
          {isLoading ? (
            <Skeleton className="h-28 rounded-2xl" />
          ) : members.length === 0 ? (
            <Empty className="min-h-56 rounded-2xl border border-dashed border-border/70 bg-muted/10">
              <EmptyContent>
                <EmptyMedia variant="icon">
                  <Users className="size-5" />
                </EmptyMedia>
                <EmptyHeader>
                  <EmptyTitle>{t("workspaces.members.title")}</EmptyTitle>
                  <EmptyDescription>
                    {t("workspaces.members.empty")}
                  </EmptyDescription>
                </EmptyHeader>
              </EmptyContent>
            </Empty>
          ) : (
            members.map((member) => (
              <div
                key={member.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-card p-4"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{member.userId}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("workspaces.members.joinedAt", {
                      date: formatDateTime(member.joinedAt),
                    })}
                  </p>
                </div>
                <Badge variant={member.role === "owner" ? "default" : "outline"}>
                  <Shield className="size-3" />
                  {formatWorkspaceRole(t, member.role)}
                </Badge>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </TeamShell>
  );
}

export function TeamInvitesPageClient() {
  const { t } = useT("translation");
  const { currentWorkspace } = useWorkspaceContext();
  const [invites, setInvites] = React.useState<WorkspaceInvite[]>([]);
  const [role, setRole] = React.useState<WorkspaceRole>("member");
  const [isLoading, setIsLoading] = React.useState(true);
  const [isMutating, setIsMutating] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!currentWorkspace) return;
    setIsLoading(true);
    try {
      setInvites(await workspacesApi.listInvites(currentWorkspace.id));
    } catch (error) {
      console.error("[Workspaces] invites refresh failed", error);
      toast.error(t("workspaces.toasts.loadFailed"));
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkspace, t]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const createInvite = async () => {
    if (!currentWorkspace) return;
    setIsMutating(true);
    try {
      const invite = await workspacesApi.createInvite(currentWorkspace.id, {
        role,
        expiresInDays: 7,
        maxUses: 1,
      });
      setInvites((prev) => [invite, ...prev]);
      toast.success(t("workspaces.toasts.inviteCreated"));
    } catch (error) {
      console.error("[Workspaces] invite create failed", error);
      toast.error(t("workspaces.toasts.inviteFailed"));
    } finally {
      setIsMutating(false);
    }
  };

  const copyInviteToken = async (token: string) => {
    await navigator.clipboard.writeText(token);
    toast.success(t("workspaces.toasts.inviteCopied"));
  };

  return (
    <TeamShell
      activePage="invites"
      title={t("workspaces.pages.invites.title")}
      subtitle={t("workspaces.invites.description")}
      toolbarActions={
        <>
          <Select value={role} onValueChange={(value) => setRole(value as WorkspaceRole)}>
            <SelectTrigger className="w-full sm:w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(["admin", "member"] as const).map((item) => (
                <SelectItem key={item} value={item}>
                  {formatWorkspaceRole(t, item)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            type="button"
            onClick={() => void createInvite()}
            disabled={isMutating || !currentWorkspace}
          >
            <Ticket className="size-4" />
            {t("workspaces.invites.createAction")}
          </Button>
        </>
      }
    >
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle>{t("workspaces.invites.title")}</CardTitle>
          <CardDescription>{t("workspaces.invites.description")}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 pb-6">
          {isLoading ? (
            <Skeleton className="h-28 rounded-2xl" />
          ) : invites.length === 0 ? (
            <Empty className="min-h-56 rounded-2xl border border-dashed border-border/70 bg-muted/10">
              <EmptyContent>
                <EmptyMedia variant="icon">
                  <Ticket className="size-5" />
                </EmptyMedia>
                <EmptyHeader>
                  <EmptyTitle>{t("workspaces.invites.title")}</EmptyTitle>
                  <EmptyDescription>
                    {t("workspaces.invites.empty")}
                  </EmptyDescription>
                </EmptyHeader>
              </EmptyContent>
            </Empty>
          ) : (
            invites.map((invite) => (
              <div
                key={invite.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border/60 bg-card p-4"
              >
                <div className="min-w-0">
                  <p className="truncate font-mono text-sm">{invite.token}</p>
                  <p className="text-xs text-muted-foreground">
                    {t("workspaces.invites.expiresAt", {
                      date: formatDateTime(invite.expiresAt),
                    })}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={invite.revokedAt ? "secondary" : "outline"}>
                    {invite.revokedAt
                      ? t("workspaces.invites.revoked")
                      : formatWorkspaceRole(t, invite.role)}
                  </Badge>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => void copyInviteToken(invite.token)}
                  >
                    <Copy className="size-4" />
                    {t("workspaces.invites.copy")}
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </TeamShell>
  );
}
