import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  ActivityLog,
  Workspace,
  WorkspaceInvite,
  WorkspaceMember,
  WorkspaceRole,
} from "@/features/workspaces/model/types";

interface WorkspaceResponse {
  workspace_id: string;
  name: string;
  slug: string;
  kind: "personal" | "shared";
  owner_user_id: string;
  created_at: string;
  updated_at: string;
}

interface WorkspaceMemberResponse {
  membership_id: number;
  workspace_id: string;
  user_id: string;
  role: WorkspaceRole;
  joined_at: string;
  invited_by: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

interface WorkspaceInviteResponse {
  invite_id: string;
  workspace_id: string;
  token: string;
  role: WorkspaceRole;
  expires_at: string;
  created_by: string;
  max_uses: number;
  used_count: number;
  revoked_at: string | null;
  created_at: string;
  updated_at: string;
}

interface ActivityLogResponse {
  activity_log_id: string;
  workspace_id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

function mapWorkspace(workspace: WorkspaceResponse): Workspace {
  return {
    id: workspace.workspace_id,
    name: workspace.name,
    slug: workspace.slug,
    kind: workspace.kind,
    ownerUserId: workspace.owner_user_id,
    createdAt: workspace.created_at,
    updatedAt: workspace.updated_at,
  };
}

function mapMember(member: WorkspaceMemberResponse): WorkspaceMember {
  return {
    id: member.membership_id,
    workspaceId: member.workspace_id,
    userId: member.user_id,
    role: member.role,
    joinedAt: member.joined_at,
    invitedBy: member.invited_by,
    status: member.status,
    createdAt: member.created_at,
    updatedAt: member.updated_at,
  };
}

function mapInvite(invite: WorkspaceInviteResponse): WorkspaceInvite {
  return {
    id: invite.invite_id,
    workspaceId: invite.workspace_id,
    token: invite.token,
    role: invite.role,
    expiresAt: invite.expires_at,
    createdBy: invite.created_by,
    maxUses: invite.max_uses,
    usedCount: invite.used_count,
    revokedAt: invite.revoked_at,
    createdAt: invite.created_at,
    updatedAt: invite.updated_at,
  };
}

function mapActivityLog(activity: ActivityLogResponse): ActivityLog {
  return {
    id: activity.activity_log_id,
    workspaceId: activity.workspace_id,
    actorUserId: activity.actor_user_id,
    action: activity.action,
    targetType: activity.target_type,
    targetId: activity.target_id,
    metadata: activity.metadata,
    createdAt: activity.created_at,
  };
}

export const workspacesApi = {
  listWorkspaces: async (): Promise<Workspace[]> => {
    const workspaces = await apiClient.get<WorkspaceResponse[]>(
      API_ENDPOINTS.workspaces,
    );
    return workspaces.map(mapWorkspace);
  },

  createWorkspace: async (name: string): Promise<Workspace> => {
    const workspace = await apiClient.post<WorkspaceResponse>(
      API_ENDPOINTS.workspaces,
      { name },
    );
    return mapWorkspace(workspace);
  },

  listMembers: async (workspaceId: string): Promise<WorkspaceMember[]> => {
    const members = await apiClient.get<WorkspaceMemberResponse[]>(
      API_ENDPOINTS.workspaceMembers(workspaceId),
    );
    return members.map(mapMember);
  },

  listInvites: async (workspaceId: string): Promise<WorkspaceInvite[]> => {
    const invites = await apiClient.get<WorkspaceInviteResponse[]>(
      API_ENDPOINTS.workspaceInvites(workspaceId),
    );
    return invites.map(mapInvite);
  },

  createInvite: async (
    workspaceId: string,
    input: { role: WorkspaceRole; expiresInDays: number; maxUses: number },
  ): Promise<WorkspaceInvite> => {
    const invite = await apiClient.post<WorkspaceInviteResponse>(
      API_ENDPOINTS.workspaceInvites(workspaceId),
      {
        role: input.role,
        expires_in_days: input.expiresInDays,
        max_uses: input.maxUses,
      },
    );
    return mapInvite(invite);
  },

  revokeInvite: async (
    workspaceId: string,
    inviteId: string,
  ): Promise<WorkspaceInvite> => {
    const invite = await apiClient.post<WorkspaceInviteResponse>(
      API_ENDPOINTS.workspaceInviteRevoke(workspaceId, inviteId),
      {},
    );
    return mapInvite(invite);
  },

  listActivity: async (workspaceId: string): Promise<ActivityLog[]> => {
    const activity = await apiClient.get<ActivityLogResponse[]>(
      API_ENDPOINTS.workspaceActivity(workspaceId),
    );
    return activity.map(mapActivityLog);
  },
};
