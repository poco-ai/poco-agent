import type {
  ServerAgentItem,
  ServerInviteItem,
  ServerMemberItem,
} from "@/features/servers/model/types";

export interface ServerMembershipApi {
  listAgents: (serverId: string) => Promise<ServerAgentItem[]>;
  listMembers: (serverId: string) => Promise<ServerMemberItem[]>;
  listInvites: (serverId: string) => Promise<ServerInviteItem[]>;
}

export interface ServerMembershipData {
  agents: ServerAgentItem[];
  members: ServerMemberItem[];
  invites: ServerInviteItem[];
}

export async function loadServerMembershipData(
  serverId: string,
  api: ServerMembershipApi,
): Promise<ServerMembershipData> {
  const [agents, members] = await Promise.all([
    api.listAgents(serverId),
    api.listMembers(serverId),
  ]);

  let invites: ServerInviteItem[] = [];
  try {
    invites = await api.listInvites(serverId);
  } catch {
    invites = [];
  }

  return {
    agents,
    members,
    invites,
  };
}
