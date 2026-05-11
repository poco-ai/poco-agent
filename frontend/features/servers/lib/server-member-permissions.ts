import type { ServerKind, ServerMemberItem, ServerRole } from "../model/types";

const SERVER_ROLES: readonly ServerRole[] = ["owner", "admin", "member"];

export interface ServerMemberPermissionInput {
  currentUserId?: string | null;
  currentUserRole?: string | null;
  targetMember: ServerMemberItem;
  serverKind?: ServerKind | null;
}

export interface InvitedByDisplay {
  primary: string;
  secondary: string | null;
}

export function isServerRole(
  value: string | null | undefined,
): value is ServerRole {
  return SERVER_ROLES.includes(value as ServerRole);
}

export function getServerRoleLabelKey(role: string): string {
  return isServerRole(role) ? `conversationView.roles.${role}` : role;
}

export function canManageServerOperations(
  role: string | null | undefined,
): boolean {
  return role === "owner" || role === "admin";
}

export function canManageServerMembers(
  role: string | null | undefined,
): boolean {
  return role === "owner";
}

export function canEditServerMemberRole({
  currentUserId,
  currentUserRole,
  targetMember,
}: ServerMemberPermissionInput): boolean {
  return Boolean(
    currentUserId &&
    currentUserRole === "owner" &&
    targetMember.status === "active" &&
    targetMember.role !== "owner" &&
    targetMember.userId !== currentUserId,
  );
}

export function canShowTransferServerOwnershipAction({
  currentUserId,
  currentUserRole,
  targetMember,
}: ServerMemberPermissionInput): boolean {
  return Boolean(
    currentUserId &&
    currentUserRole === "owner" &&
    targetMember.status === "active" &&
    targetMember.role !== "owner" &&
    targetMember.userId !== currentUserId,
  );
}

export function canTransferServerOwnership(
  input: ServerMemberPermissionInput,
): boolean {
  return (
    input.serverKind !== "personal" &&
    canShowTransferServerOwnershipAction(input)
  );
}

export function canRemoveServerMember({
  currentUserId,
  currentUserRole,
  targetMember,
}: ServerMemberPermissionInput): boolean {
  return Boolean(
    currentUserId &&
    currentUserRole === "owner" &&
    targetMember.status === "active" &&
    targetMember.role !== "owner" &&
    targetMember.userId !== currentUserId,
  );
}

export function getInvitedByDisplay(
  member: ServerMemberItem,
  members: ServerMemberItem[],
): InvitedByDisplay | null {
  const invitedBy = member.invitedBy?.trim();
  if (!invitedBy) {
    return null;
  }
  const inviter = members.find((item) => item.userId === invitedBy) ?? null;
  if (!inviter) {
    return { primary: invitedBy, secondary: null };
  }
  const displayName = inviter.user?.displayName?.trim() || inviter.userId;
  return {
    primary: displayName,
    secondary: displayName === invitedBy ? null : invitedBy,
  };
}
