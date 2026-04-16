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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import {
  countActiveInvites,
  getInviteState,
} from "@/features/workspaces/lib/team-overview";
import { useWorkspaceContext } from "@/features/workspaces/model/workspace-context";
import type {
  Workspace,
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
      value: String(countActiveInvites(invites)),
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

function WorkspaceOverviewHero({
  workspace,
  members,
  invites,
}: {
  workspace: Workspace | null;
  members: WorkspaceMember[];
  invites: WorkspaceInvite[];
}) {
  const { t } = useT("translation");

  return (
    <Card className="overflow-hidden border-primary/20 bg-gradient-to-br from-primary/10 via-card to-card shadow-sm">
      <CardContent className="flex flex-col gap-4 p-6 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-3">
          <Badge variant="secondary">
            {workspace
              ? formatWorkspaceKind(t, workspace.kind)
              : t("workspaces.emptyValue")}
          </Badge>
          <div className="space-y-1">
            <h2 className="text-2xl font-semibold tracking-tight text-foreground">
              {workspace?.name ?? t("workspaces.noWorkspace")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {workspace
                ? t("workspaces.currentWorkspace", { name: workspace.name })
                : t("workspaces.noWorkspace")}
            </p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {[
            {
              label: t("workspaces.summary.kind"),
              value: workspace
                ? formatWorkspaceKind(t, workspace.kind)
                : t("workspaces.emptyValue"),
            },
            {
              label: t("workspaces.summary.members"),
              value: String(members.length),
            },
            {
              label: t("workspaces.summary.invites"),
              value: String(countActiveInvites(invites)),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="rounded-2xl border border-border/60 bg-background/80 px-4 py-3 shadow-sm"
            >
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {item.label}
              </p>
              <p className="mt-2 text-lg font-semibold text-foreground">
                {item.value}
              </p>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

interface CreateInviteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialRole: WorkspaceRole;
  onCreate: (role: WorkspaceRole) => Promise<void>;
}

function CreateInviteDialog({
  open,
  onOpenChange,
  initialRole,
  onCreate,
}: CreateInviteDialogProps) {
  const { t } = useT("translation");
  const [role, setRole] = React.useState<WorkspaceRole>(initialRole);
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setRole(initialRole);
      setIsSaving(false);
    }
  }, [initialRole, open]);

  const handleCreate = async () => {
    setIsSaving(true);
    await onCreate(role);
    setIsSaving(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("workspaces.invites.createTitle")}</DialogTitle>
          <DialogDescription>
            {t("workspaces.invites.createDescription")}
          </DialogDescription>
        </DialogHeader>
        <Select value={role} onValueChange={(value) => setRole(value as WorkspaceRole)}>
          <SelectTrigger>
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
        <DialogFooter>
          <Button type="button" onClick={() => void handleCreate()} disabled={isSaving}>
            <Ticket className="size-4" />
            {t("workspaces.invites.createAction")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
          <WorkspaceOverviewHero
            workspace={currentWorkspace}
            members={members}
            invites={invites}
          />
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
  const [inviteDialogOpen, setInviteDialogOpen] = React.useState(false);

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

  const createInvite = async (nextRole: WorkspaceRole) => {
    if (!currentWorkspace) return;
    setIsMutating(true);
    try {
      const invite = await workspacesApi.createInvite(currentWorkspace.id, {
        role: nextRole,
        expiresInDays: 7,
        maxUses: 1,
      });
      setInvites((prev) => [invite, ...prev]);
      setRole(nextRole);
      setInviteDialogOpen(false);
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
        <Button
          type="button"
          onClick={() => setInviteDialogOpen(true)}
          disabled={isMutating || !currentWorkspace}
        >
            <Ticket className="size-4" />
            {t("workspaces.invites.createAction")}
        </Button>
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
                  {getInviteState(invite) === "active" ? (
                    <Badge variant="outline">
                      {formatWorkspaceRole(t, invite.role)}
                    </Badge>
                  ) : (
                    <Badge variant="secondary">
                      {getInviteState(invite) === "revoked"
                        ? t("workspaces.invites.revoked")
                        : t("workspaces.invites.expired")}
                    </Badge>
                  )}
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
      <CreateInviteDialog
        open={inviteDialogOpen}
        onOpenChange={setInviteDialogOpen}
        initialRole={role}
        onCreate={createInvite}
      />
    </TeamShell>
  );
}
