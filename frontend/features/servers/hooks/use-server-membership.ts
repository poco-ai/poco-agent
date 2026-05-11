"use client";

import * as React from "react";
import { toast } from "sonner";

import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useAdaptivePolling } from "@/features/chat/hooks/use-adaptive-polling";
import { serversApi } from "@/features/servers";
import { loadServerMembershipData } from "@/features/servers/lib/server-membership";
import type {
  ServerAgentItem,
  ServerInviteItem,
  ServerItem,
  ServerMemberItem,
  ServerRole,
} from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

export interface ServerAgentCreateInput {
  presetId: number;
  displayName: string;
  handle: string;
  description: string;
}

export function useServerMembership({
  selectedServerId,
  onServersChanged,
  onSwitchServer,
  onSelectAgent,
  onClearSelection,
}: {
  selectedServerId: string | null;
  onServersChanged: (servers: ServerItem[]) => void;
  onSwitchServer: (serverId: string) => void;
  onSelectAgent: (agent: ServerAgentItem) => void;
  onClearSelection: () => void;
}) {
  const { t } = useT("translation");
  const [serverAgents, setServerAgents] = React.useState<ServerAgentItem[]>([]);
  const [serverMembers, setServerMembers] = React.useState<ServerMemberItem[]>(
    [],
  );
  const [serverInvites, setServerInvites] = React.useState<ServerInviteItem[]>(
    [],
  );
  const [presets, setPresets] = React.useState<Preset[]>([]);
  const [isServerAccessWorking, setIsServerAccessWorking] =
    React.useState(false);
  const [isAgentCreating, setIsAgentCreating] = React.useState(false);

  const refreshMembership = React.useCallback(async (serverId: string) => {
    const next = await loadServerMembershipData(serverId, serversApi);
    setServerAgents(next.agents);
    setServerMembers(next.members);
    setServerInvites(next.invites);
  }, []);

  React.useEffect(() => {
    if (!selectedServerId) {
      setServerAgents([]);
      setServerMembers([]);
      setServerInvites([]);
      return;
    }
    void refreshMembership(selectedServerId).catch((error) => {
      console.error("[ServersWorkspace] membership load failed", error);
      toast.error(t("conversationView.toasts.loadFailed"));
    });
  }, [refreshMembership, selectedServerId, t]);

  const pollMembership = React.useCallback(async () => {
    if (!selectedServerId) {
      return;
    }
    await refreshMembership(selectedServerId);
  }, [refreshMembership, selectedServerId]);

  useAdaptivePolling({
    callback: pollMembership,
    isActive: Boolean(selectedServerId),
    interval: Number(process.env.NEXT_PUBLIC_SESSION_POLLING_INTERVAL) || 6000,
    enableBackoff: true,
  });

  React.useEffect(() => {
    const loadPresets = async () => {
      try {
        setPresets(await presetsService.listPresets({ revalidate: 0 }));
      } catch (error) {
        console.error("[ServersWorkspace] preset load failed", error);
      }
    };
    void loadPresets();
  }, []);

  const createServer = React.useCallback(
    async (name: string) => {
      const trimmed = name.trim();
      if (!trimmed) {
        return;
      }
      setIsServerAccessWorking(true);
      try {
        const created = await serversApi.createServer({ name: trimmed });
        onServersChanged(await serversApi.listServers());
        onSwitchServer(created.id);
        toast.success(t("conversationView.toasts.serverCreated"));
      } catch (error) {
        console.error("[ServersWorkspace] create server failed", error);
        toast.error(t("conversationView.toasts.serverCreateFailed"));
      } finally {
        setIsServerAccessWorking(false);
      }
    },
    [onServersChanged, onSwitchServer, t],
  );

  const acceptInvite = React.useCallback(
    async (token: string) => {
      const trimmed = token.trim();
      if (!trimmed) {
        return;
      }
      setIsServerAccessWorking(true);
      try {
        const member = await serversApi.acceptInvite({ token: trimmed });
        onServersChanged(await serversApi.listServers());
        onSwitchServer(member.serverId);
        toast.success(t("conversationView.toasts.inviteAccepted"));
      } catch (error) {
        console.error("[ServersWorkspace] accept invite failed", error);
        toast.error(t("conversationView.toasts.inviteAcceptFailed"));
      } finally {
        setIsServerAccessWorking(false);
      }
    },
    [onServersChanged, onSwitchServer, t],
  );

  const createInvite = React.useCallback(async () => {
    if (!selectedServerId) {
      return;
    }
    setIsServerAccessWorking(true);
    try {
      const invite = await serversApi.createInvite(selectedServerId);
      setServerInvites((current) => {
        const withoutExisting = current.filter((item) => item.id !== invite.id);
        return [invite, ...withoutExisting];
      });
      toast.success(t("conversationView.toasts.inviteCreated"));
    } catch (error) {
      console.error("[ServersWorkspace] create invite failed", error);
      toast.error(t("conversationView.toasts.inviteCreateFailed"));
    } finally {
      setIsServerAccessWorking(false);
    }
  }, [selectedServerId, t]);

  const copyInvite = React.useCallback(
    async (token: string) => {
      try {
        await navigator.clipboard.writeText(token);
        toast.success(t("conversationView.toasts.inviteCopied"));
      } catch (error) {
        console.error("[ServersWorkspace] copy invite failed", error);
        toast.error(t("conversationView.toasts.inviteCopyFailed"));
      }
    },
    [t],
  );

  const createAgent = React.useCallback(
    async (input: ServerAgentCreateInput) => {
      if (!selectedServerId || !input.presetId || !input.displayName.trim()) {
        return;
      }
      setIsAgentCreating(true);
      try {
        const agent = await serversApi.createAgent(selectedServerId, {
          presetId: input.presetId,
          displayName: input.displayName.trim(),
          handle: input.handle.trim() || null,
          description: input.description.trim() || null,
        });
        setServerAgents((current) => [agent, ...current]);
        onSelectAgent(agent);
        toast.success(t("conversationView.toasts.agentCreated"));
      } catch (error) {
        console.error("[ServersWorkspace] create server agent failed", error);
        toast.error(t("conversationView.toasts.agentCreateFailed"));
      } finally {
        setIsAgentCreating(false);
      }
    },
    [onSelectAgent, selectedServerId, t],
  );

  const updateAgentDescription = React.useCallback(
    async (agentId: string, description: string) => {
      if (!selectedServerId) {
        return;
      }
      try {
        const agent = await serversApi.updateAgent(selectedServerId, agentId, {
          description: description.trim() || null,
        });
        setServerAgents((current) =>
          current.map((item) => (item.id === agent.id ? agent : item)),
        );
        toast.success(t("conversationView.toasts.agentUpdated"));
      } catch (error) {
        console.error("[ServersWorkspace] update server agent failed", error);
        toast.error(t("conversationView.toasts.agentUpdateFailed"));
        throw error;
      }
    },
    [selectedServerId, t],
  );

  const updateMemberRole = React.useCallback(
    async (membershipId: number, role: ServerRole) => {
      if (!selectedServerId) {
        return;
      }
      try {
        const member = await serversApi.updateMemberRole(
          selectedServerId,
          membershipId,
          role,
        );
        setServerMembers((current) =>
          current.map((item) => (item.id === member.id ? member : item)),
        );
        toast.success(t("conversationView.toasts.memberRoleUpdated"));
      } catch (error) {
        console.error("[ServersWorkspace] update server member role failed", error);
        toast.error(t("conversationView.toasts.memberRoleUpdateFailed"));
        throw error;
      }
    },
    [selectedServerId, t],
  );

  const transferOwnership = React.useCallback(
    async (newOwnerUserId: string) => {
      if (!selectedServerId) {
        return;
      }
      try {
        const server = await serversApi.transferOwnership(
          selectedServerId,
          newOwnerUserId,
        );
        await refreshMembership(selectedServerId);
        onServersChanged(await serversApi.listServers());
        onSwitchServer(server.id);
        toast.success(t("conversationView.toasts.ownershipTransferred"));
      } catch (error) {
        console.error("[ServersWorkspace] transfer server ownership failed", error);
        toast.error(t("conversationView.toasts.ownershipTransferFailed"));
        throw error;
      }
    },
    [onServersChanged, onSwitchServer, refreshMembership, selectedServerId, t],
  );

  const removeMember = React.useCallback(
    async (membershipId: number) => {
      if (!selectedServerId) {
        return;
      }
      try {
        await serversApi.removeMember(selectedServerId, membershipId);
        await refreshMembership(selectedServerId);
        onClearSelection();
        toast.success(t("conversationView.toasts.memberRemoved"));
      } catch (error) {
        console.error("[ServersWorkspace] remove server member failed", error);
        toast.error(t("conversationView.toasts.memberRemoveFailed"));
      }
    },
    [onClearSelection, refreshMembership, selectedServerId, t],
  );

  return {
    serverAgents,
    serverMembers,
    serverInvites,
    presets,
    isServerAccessWorking,
    isAgentCreating,
    createServer,
    acceptInvite,
    createInvite,
    copyInvite,
    createAgent,
    updateAgentDescription,
    updateMemberRole,
    transferOwnership,
    removeMember,
    refreshMembership,
  };
}
