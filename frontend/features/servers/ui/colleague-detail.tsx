"use client";

import * as React from "react";
import {
  ArrowLeft,
  CalendarDays,
  Check,
  MessageSquare,
  Pencil,
  Pin,
  Power,
  RotateCw,
  Shield,
  Trash2,
  UserPlus,
  UserRound,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { PersistentRuntimeBadge } from "@/components/shared/persistent-runtime-badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { serversApi } from "@/features/servers";
import type { FileNode } from "@/features/chat/types";
import {
  getUserAvatarUrl,
  getUserDisplayName,
} from "@/features/servers/lib/server-conversation-view";
import {
  canEditServerMemberRole,
  canRemoveServerMember,
  canShowTransferServerOwnershipAction,
  canTransferServerOwnership,
  getInvitedByDisplay,
  getServerRoleLabelKey,
  isServerRole,
} from "@/features/servers/lib/server-member-permissions";
import { getAgentRuntimeStatus } from "@/features/servers/lib/agent-runtime-status";
import type {
  ServerAgentItem,
  ServerChannelMemberItem,
  ServerKind,
  ServerMemberItem,
  ServerRole,
} from "@/features/servers/model/types";
import type { ColleagueSelection } from "@/features/servers/ui/server-workspace-types";
import { useT } from "@/lib/i18n/client";
import { ServerAgentAvatar } from "./server-agent-avatar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { AgentPersistentFilesPanel } from "./agent-persistent-files-panel";

const agentPersistentFilesCache = new Map<string, FileNode[]>();

export function ColleagueDetail({
  selection,
  agents,
  presets,
  members,
  serverId,
  serverKind,
  canInspectPersistentFiles,
  currentUserId,
  currentServerRole,
  canManageServerOperations,
  canManageServerMembers,
  activeChannelId,
  channelMembers = [],
  activeChannelIdByAgentId = {},
  channelNamesByAgentId = {},
  onClose,
  onOpenDm,
  onOpenActiveChannel,
  onUpdateMemberRole,
  onTransferOwnership,
  onRemoveMember,
  onRestartAgent,
  onStopAgent,
  onPinAgentRuntime,
  onUnpinAgentRuntime,
  onUpdateAgentDescription,
  onRemoveAgentFromServer,
  onRemoveMemberFromChannel,
}: {
  selection: ColleagueSelection | null;
  agents: ServerAgentItem[];
  presets: Preset[];
  members: ServerMemberItem[];
  serverId?: string | null;
  serverKind?: ServerKind | null;
  canInspectPersistentFiles?: boolean;
  currentUserId?: string | null;
  currentServerRole?: string | null;
  canManageServerOperations?: boolean;
  canManageServerMembers?: boolean;
  activeChannelId?: string | null;
  channelMembers?: ServerChannelMemberItem[];
  activeChannelIdByAgentId?: Record<string, string>;
  channelNamesByAgentId?: Record<string, string[]>;
  onClose: () => void;
  onOpenDm: (agentId: string) => void;
  onOpenActiveChannel?: (channelId: string) => void;
  onUpdateMemberRole: (membershipId: number, role: ServerRole) => Promise<void>;
  onTransferOwnership: (userId: string) => Promise<void>;
  onRemoveMember: (membershipId: number) => void;
  onRestartAgent: (agentId: string) => void;
  onStopAgent: (agentId: string) => void;
  onPinAgentRuntime: (agentId: string, durationHours: number) => Promise<void>;
  onUnpinAgentRuntime: (agentId: string) => Promise<void>;
  onUpdateAgentDescription: (
    agentId: string,
    description: string,
  ) => Promise<void>;
  onRemoveAgentFromServer: (agentId: string) => void;
  onRemoveMemberFromChannel: (membershipId: number) => void;
}) {
  const { t } = useT("translation");
  const selectedAgent =
    selection?.kind === "agent"
      ? (agents.find((agent) => agent.id === selection.id) ?? null)
      : null;
  const selectedMember =
    selection?.kind === "human"
      ? (members.find((member) => member.id === selection.id) ?? null)
      : null;
  const selectedRuntimeStatus = selectedAgent
    ? getAgentRuntimeStatus(selectedAgent)
    : null;
  const selectedAgentId = selectedAgent?.id ?? null;
  const selectedAgentRemoved = Boolean(selectedAgent?.removedAt);
  const selectedAgentActiveChannelId = selectedAgent
    ? (activeChannelIdByAgentId[selectedAgent.id] ?? "")
    : "";
  const selectedMemberChannelMembership =
    selectedMember && activeChannelId
      ? (channelMembers.find(
          (member) => member.userId === selectedMember.userId,
        ) ?? null)
      : null;
  const invitedByDisplay = selectedMember
    ? getInvitedByDisplay(selectedMember, members)
    : null;
  const canEditSelectedMemberRole = selectedMember
    ? canEditServerMemberRole({
        currentUserId,
        currentUserRole: currentServerRole,
        targetMember: selectedMember,
      })
    : false;
  const canShowTransferSelectedMemberOwnership = selectedMember
    ? canShowTransferServerOwnershipAction({
        currentUserId,
        currentUserRole: currentServerRole,
        targetMember: selectedMember,
      })
    : false;
  const canTransferSelectedMemberOwnership = selectedMember
    ? canTransferServerOwnership({
        currentUserId,
        currentUserRole: currentServerRole,
        targetMember: selectedMember,
        serverKind,
      })
    : false;
  const isPersonalServer = serverKind === "personal";
  const canRemoveSelectedMember = selectedMember
    ? canRemoveServerMember({
        currentUserId,
        currentUserRole: currentServerRole,
        targetMember: selectedMember,
      })
    : false;
  const [persistentFiles, setPersistentFiles] = React.useState<FileNode[]>([]);
  const [isLoadingPersistentFiles, setIsLoadingPersistentFiles] =
    React.useState(false);
  const [removeAgentConfirmOpen, setRemoveAgentConfirmOpen] =
    React.useState(false);
  const [restartAgentConfirmOpen, setRestartAgentConfirmOpen] =
    React.useState(false);
  const [stopAgentConfirmOpen, setStopAgentConfirmOpen] = React.useState(false);
  const [pinDialogOpen, setPinDialogOpen] = React.useState(false);
  const [pinDurationHours, setPinDurationHours] = React.useState("1");
  const [isUpdatingPin, setIsUpdatingPin] = React.useState(false);
  const [isEditingDescription, setIsEditingDescription] = React.useState(false);
  const [descriptionDraft, setDescriptionDraft] = React.useState("");
  const [isSavingDescription, setIsSavingDescription] = React.useState(false);
  const [isUpdatingMemberRole, setIsUpdatingMemberRole] = React.useState(false);
  const [transferOwnershipConfirmOpen, setTransferOwnershipConfirmOpen] =
    React.useState(false);
  const selectedAgentChannelNames = selectedAgent
    ? (channelNamesByAgentId[selectedAgent.id] ?? [])
    : [];
  const selectedAgentStopped =
    (selectedAgent?.lifecycleState || "").trim().toLowerCase() === "inactive";
  const selectedAgentPinned = selectedRuntimeStatus?.isPinned ?? false;

  React.useEffect(() => {
    setIsEditingDescription(false);
    setDescriptionDraft(selectedAgent?.description ?? "");
    setIsSavingDescription(false);
  }, [selectedAgent?.description, selectedAgent?.id]);

  React.useEffect(() => {
    if (!selectedAgent?.runtimeSummary?.keepaliveUntil) {
      setPinDurationHours("1");
      return;
    }
    const keepaliveUntil = new Date(
      selectedAgent.runtimeSummary.keepaliveUntil,
    );
    if (Number.isNaN(keepaliveUntil.getTime())) {
      setPinDurationHours("1");
      return;
    }
    const remainingHours = Math.max(
      1,
      Math.ceil((keepaliveUntil.getTime() - Date.now()) / (60 * 60 * 1000)),
    );
    setPinDurationHours(String(remainingHours));
  }, [selectedAgent?.id, selectedAgent?.runtimeSummary?.keepaliveUntil]);

  const handleDescriptionAction = async () => {
    if (!selectedAgent || selectedAgentRemoved || isSavingDescription) {
      return;
    }
    if (!isEditingDescription) {
      setDescriptionDraft(selectedAgent.description ?? "");
      setIsEditingDescription(true);
      return;
    }
    setIsSavingDescription(true);
    try {
      await onUpdateAgentDescription(selectedAgent.id, descriptionDraft);
      setIsEditingDescription(false);
    } finally {
      setIsSavingDescription(false);
    }
  };

  const handleMemberRoleChange = async (role: string) => {
    if (
      !selectedMember ||
      !isServerRole(role) ||
      role === "owner" ||
      role === selectedMember.role ||
      isUpdatingMemberRole
    ) {
      return;
    }
    setIsUpdatingMemberRole(true);
    try {
      await onUpdateMemberRole(selectedMember.id, role);
    } finally {
      setIsUpdatingMemberRole(false);
    }
  };

  const handleTransferOwnership = async () => {
    if (!selectedMember || !canTransferSelectedMemberOwnership) {
      return;
    }
    await onTransferOwnership(selectedMember.userId);
  };

  const handlePinRuntime = async () => {
    if (!selectedAgent || selectedAgentRemoved || isUpdatingPin) {
      return;
    }
    const parsedHours = Number.parseInt(pinDurationHours, 10);
    if (!Number.isFinite(parsedHours) || parsedHours < 1 || parsedHours > 24) {
      return;
    }
    setIsUpdatingPin(true);
    try {
      await onPinAgentRuntime(selectedAgent.id, parsedHours);
      setPinDialogOpen(false);
    } finally {
      setIsUpdatingPin(false);
    }
  };

  const handleUnpinRuntime = async () => {
    if (!selectedAgent || selectedAgentRemoved || isUpdatingPin) {
      return;
    }
    setIsUpdatingPin(true);
    try {
      await onUnpinAgentRuntime(selectedAgent.id);
      setPinDialogOpen(false);
    } finally {
      setIsUpdatingPin(false);
    }
  };

  React.useEffect(() => {
    if (!canInspectPersistentFiles || !serverId || !selectedAgentId) {
      setPersistentFiles([]);
      return;
    }
    const cacheKey = `${serverId}:${selectedAgentId}`;
    const cachedFiles = agentPersistentFilesCache.get(cacheKey);
    if (cachedFiles) {
      setPersistentFiles(cachedFiles);
      setIsLoadingPersistentFiles(false);
      return;
    }
    let cancelled = false;
    const load = async () => {
      try {
        setIsLoadingPersistentFiles(true);
        const files = await serversApi.listAgentStateFiles(
          serverId,
          selectedAgentId,
        );
        if (!cancelled) {
          agentPersistentFilesCache.set(cacheKey, files);
          setPersistentFiles(files);
        }
      } catch (error) {
        console.error(
          "[ColleagueDetail] failed to load persistent files",
          error,
        );
        if (!cancelled) {
          setPersistentFiles([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingPersistentFiles(false);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, [canInspectPersistentFiles, selectedAgentId, serverId]);

  return (
    <aside className="absolute inset-y-0 right-0 z-30 flex w-full flex-col border-l border-border bg-card md:left-[17rem] md:w-auto lg:left-[18rem] xl:static xl:h-full xl:w-full xl:min-w-0 xl:shrink-0">
      <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <p className="text-base font-semibold text-foreground">
            {t("conversationView.colleagues.detailTitle")}
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-hidden">
        {selectedAgent ? (
          <div className="flex h-full min-h-0 flex-col gap-5 px-6 py-6">
            <div className="flex items-start gap-4">
              <ServerAgentAvatar
                agent={selectedAgent}
                presets={presets}
                className="size-14 shrink-0"
                fallbackClassName="text-lg"
              />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-3">
                  <p className="truncate text-lg font-semibold text-foreground">
                    {selectedAgent.displayName}
                  </p>
                  {selectedRuntimeStatus ? (
                    <PersistentRuntimeBadge
                      status={selectedRuntimeStatus}
                      label={t(selectedRuntimeStatus.labelKey)}
                      pinnedLabel={t("runtime.labels.pinned")}
                    />
                  ) : null}
                </div>
                <div className="mt-1 flex flex-wrap items-center gap-2">
                  <p className="text-sm text-muted-foreground">
                    @{selectedAgent.handle}
                  </p>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => onOpenDm(selectedAgent.id)}
                    disabled={selectedAgentRemoved}
                    className="h-7 pl-3.5 pr-3"
                  >
                    <MessageSquare className="size-3.5" />
                    {t("conversationView.messageAgent")}
                  </Button>
                </div>
              </div>
            </div>
            <div className="rounded-md border border-border bg-background px-4 py-4">
              <div className="flex items-center gap-2">
                <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                  {t("conversationView.colleagues.description")}
                </p>
                {canManageServerOperations && !selectedAgentRemoved ? (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    onClick={() => void handleDescriptionAction()}
                    disabled={isSavingDescription}
                    aria-label={
                      isEditingDescription
                        ? t("conversationView.colleagues.saveDescription")
                        : t("conversationView.colleagues.editDescription")
                    }
                    className="size-6 text-muted-foreground hover:text-foreground"
                  >
                    {isEditingDescription ? (
                      <Check className="size-4" />
                    ) : (
                      <Pencil className="size-4" />
                    )}
                  </Button>
                ) : null}
              </div>
              {isEditingDescription ? (
                <textarea
                  value={descriptionDraft}
                  onChange={(event) => setDescriptionDraft(event.target.value)}
                  rows={4}
                  className="mt-3 min-h-24 w-full resize-y rounded-md border border-border bg-background px-3 py-2 text-sm leading-6 text-foreground outline-none transition-colors placeholder:text-muted-foreground focus:border-primary/50"
                  placeholder={t(
                    "conversationView.colleagues.agentDescriptionPlaceholder",
                  )}
                />
              ) : (
                <p className="mt-3 text-sm leading-6 text-foreground">
                  {selectedAgent.description ||
                    t("conversationView.colleagues.agentEmptyDescription")}
                </p>
              )}
            </div>
            {canInspectPersistentFiles && selectedAgent.persistentState ? (
              <div className="flex min-h-0 flex-1 flex-col space-y-3 overflow-hidden px-1 py-1">
                <div className="shrink-0 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    {t("conversationView.colleagues.persistentFiles")}
                  </p>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t("conversationView.colleagues.persistentFilesHint")}
                  </p>
                </div>
                <AgentPersistentFilesPanel
                  files={persistentFiles}
                  isLoading={isLoadingPersistentFiles}
                  emptyMessage={t(
                    "conversationView.colleagues.persistentFilesEmpty",
                  )}
                  className="min-h-0 flex-1"
                />
              </div>
            ) : null}
            <div className="mt-auto flex shrink-0 flex-wrap justify-end gap-2 border-t border-border pt-5">
              {selectedRuntimeStatus?.state === "running" &&
              selectedAgentActiveChannelId &&
              onOpenActiveChannel ? (
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    onOpenActiveChannel(selectedAgentActiveChannelId)
                  }
                >
                  <MessageSquare className="size-4" />
                  {t("conversationView.backToContext")}
                </Button>
              ) : null}
              {canManageServerOperations ? (
                <>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setPinDialogOpen(true)}
                    disabled={selectedAgentRemoved || selectedAgentStopped}
                  >
                    <Pin className="size-4" />
                    {selectedAgentPinned
                      ? t("runtime.actions.pinned")
                      : t("runtime.actions.pin")}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => setRestartAgentConfirmOpen(true)}
                    disabled={selectedAgentRemoved}
                  >
                    <RotateCw className="size-4" />
                    {selectedAgentStopped
                      ? t("conversationView.colleagues.startAgent")
                      : t("conversationView.colleagues.restartAgent")}
                  </Button>
                  {!selectedAgentStopped ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      onClick={() => setStopAgentConfirmOpen(true)}
                      disabled={selectedAgentRemoved}
                    >
                      <Power className="size-4" />
                      {t("conversationView.colleagues.stopAgent")}
                    </Button>
                  ) : null}
                  <AlertDialog
                    open={restartAgentConfirmOpen}
                    onOpenChange={setRestartAgentConfirmOpen}
                  >
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          {selectedAgentStopped
                            ? t("conversationView.colleagues.startAgentTitle", {
                                name: selectedAgent.displayName,
                              })
                            : t(
                                "conversationView.colleagues.restartAgentTitle",
                                {
                                  name: selectedAgent.displayName,
                                },
                              )}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {selectedAgentStopped
                            ? t(
                                "conversationView.colleagues.startAgentDescription",
                              )
                            : t(
                                "conversationView.colleagues.restartAgentDescription",
                              )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>
                          {t("common.cancel")}
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => {
                            onRestartAgent(selectedAgent.id);
                            setRestartAgentConfirmOpen(false);
                          }}
                        >
                          {selectedAgentStopped
                            ? t("conversationView.colleagues.startAgent")
                            : t("conversationView.colleagues.restartAgent")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  <AlertDialog
                    open={stopAgentConfirmOpen}
                    onOpenChange={setStopAgentConfirmOpen}
                  >
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          {t("conversationView.colleagues.stopAgentTitle", {
                            name: selectedAgent.displayName,
                          })}
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          {t(
                            "conversationView.colleagues.stopAgentDescription",
                          )}
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>
                          {t("common.cancel")}
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => {
                            onStopAgent(selectedAgent.id);
                            setStopAgentConfirmOpen(false);
                          }}
                        >
                          {t("conversationView.colleagues.stopAgent")}
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                  {!selectedAgentRemoved ? (
                    <AlertDialog
                      open={removeAgentConfirmOpen}
                      onOpenChange={setRemoveAgentConfirmOpen}
                    >
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        onClick={() => setRemoveAgentConfirmOpen(true)}
                        className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                      >
                        <Trash2 className="size-4" />
                        {t("conversationView.colleagues.remove")}
                      </Button>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>
                            {t("conversationView.colleagues.removeAgentTitle", {
                              name: selectedAgent.displayName,
                            })}
                          </AlertDialogTitle>
                          <AlertDialogDescription>
                            {selectedAgentChannelNames.length > 0
                              ? t(
                                  "conversationView.colleagues.removeAgentDescription",
                                  {
                                    channels: selectedAgentChannelNames
                                      .slice(0, 3)
                                      .join(", "),
                                  },
                                )
                              : t(
                                  "conversationView.colleagues.removeAgentDescriptionUnknown",
                                )}
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>
                            {t("common.cancel")}
                          </AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => {
                              onRemoveAgentFromServer(selectedAgent.id);
                              setRemoveAgentConfirmOpen(false);
                            }}
                          >
                            {t("conversationView.colleagues.remove")}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  ) : null}
                </>
              ) : null}
            </div>
          </div>
        ) : selectedMember ? (
          <div className="h-full space-y-5 overflow-y-auto px-6 py-6">
            <div className="flex items-start gap-4">
              {getUserAvatarUrl(selectedMember.user) ? (
                <Avatar className="size-14 shrink-0 rounded-md border border-border">
                  <AvatarImage
                    src={getUserAvatarUrl(selectedMember.user) ?? undefined}
                    alt={getUserDisplayName(
                      selectedMember.user,
                      selectedMember.userId,
                    )}
                  />
                  <AvatarFallback className="rounded-md bg-muted text-lg font-semibold text-foreground">
                    {getUserDisplayName(
                      selectedMember.user,
                      selectedMember.userId,
                    )
                      .charAt(0)
                      .toUpperCase()}
                  </AvatarFallback>
                </Avatar>
              ) : (
                <span className="flex size-14 shrink-0 items-center justify-center rounded-md border border-border bg-muted text-foreground">
                  <UserRound className="size-6" />
                </span>
              )}
              <div className="min-w-0">
                <p className="truncate text-lg font-semibold text-foreground">
                  {getUserDisplayName(
                    selectedMember.user,
                    selectedMember.userId,
                  )}
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {selectedMember.status}
                </p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-md border border-border bg-background px-4 py-3">
                <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                  <Shield className="size-4" />
                  {t("conversationView.colleagues.role")}
                </p>
                {canEditSelectedMemberRole ? (
                  <Select
                    value={selectedMember.role}
                    onValueChange={(value) =>
                      void handleMemberRoleChange(value)
                    }
                    disabled={isUpdatingMemberRole}
                  >
                    <SelectTrigger className="mt-2 w-full border-border bg-card">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="admin">
                        {t("conversationView.roles.admin")}
                      </SelectItem>
                      <SelectItem value="member">
                        {t("conversationView.roles.member")}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                ) : (
                  <>
                    <p className="mt-2 break-all text-sm text-foreground">
                      {t(getServerRoleLabelKey(selectedMember.role))}
                    </p>
                    {!canManageServerMembers ? (
                      <p className="mt-2 text-xs text-muted-foreground">
                        {t("conversationView.colleagues.rolePermissionHint")}
                      </p>
                    ) : null}
                  </>
                )}
              </div>
              <InfoTile
                icon={<CalendarDays className="size-4" />}
                label={t("conversationView.colleagues.joined")}
                value={selectedMember.joinedAt}
              />
            </div>
            <div className="rounded-md border border-border bg-background px-4 py-3">
              <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
                <UserPlus className="size-4" />
                {t("conversationView.colleagues.invitedBy")}
              </p>
              <p className="mt-2 break-all text-sm text-foreground">
                {invitedByDisplay?.primary ??
                  t("conversationView.colleagues.emptyValue")}
              </p>
              {invitedByDisplay?.secondary ? (
                <p className="mt-1 break-all text-xs text-muted-foreground">
                  {invitedByDisplay.secondary}
                </p>
              ) : null}
            </div>
            <div className="space-y-3 border-t border-border pt-5">
              <div className="flex flex-wrap gap-2">
                {canManageServerOperations &&
                selectedMemberChannelMembership ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      onRemoveMemberFromChannel(
                        selectedMemberChannelMembership.id,
                      )
                    }
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Trash2 className="size-4" />
                    {t("conversationView.colleagues.removeFromChannel")}
                  </Button>
                ) : null}
                {canShowTransferSelectedMemberOwnership ? (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setTransferOwnershipConfirmOpen(true)}
                    disabled={!canTransferSelectedMemberOwnership}
                    title={
                      isPersonalServer
                        ? t(
                            "conversationView.colleagues.personalOwnershipTransferHint",
                          )
                        : undefined
                    }
                    className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                  >
                    <Shield className="size-4" />
                    {t("conversationView.colleagues.transferOwnership")}
                  </Button>
                ) : null}
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onRemoveMember(selectedMember.id)}
                  disabled={!canRemoveSelectedMember}
                  title={
                    canRemoveSelectedMember
                      ? undefined
                      : t(
                          "conversationView.colleagues.ownerOnlyMemberActionHint",
                        )
                  }
                  className="text-destructive hover:bg-destructive/10 hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                  {t("conversationView.colleagues.removeMember")}
                </Button>
              </div>
              {isPersonalServer && canShowTransferSelectedMemberOwnership ? (
                <p className="text-xs text-muted-foreground">
                  {t(
                    "conversationView.colleagues.personalOwnershipTransferHint",
                  )}
                </p>
              ) : null}
              {!canManageServerMembers ? (
                <p className="text-xs text-muted-foreground">
                  {t("conversationView.colleagues.ownerOnlyMemberActionHint")}
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="flex h-full items-center justify-center px-6 py-12 text-center text-sm text-muted-foreground">
            {t("conversationView.colleagues.emptySelection")}
          </div>
        )}
      </div>
      {selectedMember ? (
        <AlertDialog
          open={transferOwnershipConfirmOpen}
          onOpenChange={setTransferOwnershipConfirmOpen}
        >
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {t("conversationView.colleagues.transferOwnershipTitle")}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {t("conversationView.colleagues.transferOwnershipDescription", {
                  member: getUserDisplayName(
                    selectedMember.user,
                    selectedMember.userId,
                  ),
                })}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>{t("common.cancel")}</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => void handleTransferOwnership()}
                className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              >
                {t("conversationView.colleagues.transferOwnership")}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      ) : null}
      <Dialog open={pinDialogOpen} onOpenChange={setPinDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("runtime.actions.pin")}</DialogTitle>
            <DialogDescription>
              {t("runtime.descriptions.pinAgent")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label
              htmlFor="agent-pin-hours"
              className="text-sm font-medium text-foreground"
            >
              {t("runtime.fields.durationHours")}
            </label>
            <Input
              id="agent-pin-hours"
              type="number"
              min={1}
              max={24}
              step={1}
              value={pinDurationHours}
              onChange={(event) => setPinDurationHours(event.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              {t("runtime.descriptions.pinAgentHint")}
            </p>
          </div>
          <DialogFooter className="gap-2 sm:justify-between">
            {selectedAgentPinned ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => void handleUnpinRuntime()}
                disabled={isUpdatingPin}
              >
                {t("runtime.actions.unpin")}
              </Button>
            ) : (
              <span />
            )}
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                onClick={() => setPinDialogOpen(false)}
                disabled={isUpdatingPin}
              >
                {t("common.cancel")}
              </Button>
              <Button
                type="button"
                onClick={() => void handlePinRuntime()}
                disabled={isUpdatingPin}
              >
                {selectedAgentPinned
                  ? t("runtime.actions.updatePin")
                  : t("runtime.actions.pin")}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </aside>
  );
}

function InfoTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-md border border-border bg-background px-4 py-3">
      <p className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
        {icon}
        {label}
      </p>
      <p className="mt-2 break-all text-sm text-foreground">{value}</p>
    </div>
  );
}
