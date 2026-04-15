export type WorkspaceRole = "owner" | "admin" | "member";

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  kind: "personal" | "shared";
  ownerUserId: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceMember {
  id: number;
  workspaceId: string;
  userId: string;
  role: WorkspaceRole;
  joinedAt: string;
  invitedBy: string | null;
  status: string;
  createdAt: string;
  updatedAt: string;
}

export interface WorkspaceInvite {
  id: string;
  workspaceId: string;
  token: string;
  role: WorkspaceRole;
  expiresAt: string;
  createdBy: string;
  maxUses: number;
  usedCount: number;
  revokedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface ActivityLog {
  id: string;
  workspaceId: string;
  actorUserId: string | null;
  action: string;
  targetType: string;
  targetId: string;
  metadata: Record<string, unknown>;
  createdAt: string;
}
