import type { WorkspaceInvite } from "../model/types.ts";

export type WorkspaceInviteState = "active" | "revoked" | "expired";

export function countActiveInvites(invites: WorkspaceInvite[]): number {
  return invites.filter((invite) => invite.revokedAt === null).length;
}

export function getInviteState(
  invite: Pick<WorkspaceInvite, "revokedAt" | "expiresAt">,
  now: Date = new Date(),
): WorkspaceInviteState {
  if (invite.revokedAt) {
    return "revoked";
  }

  return new Date(invite.expiresAt).getTime() < now.getTime()
    ? "expired"
    : "active";
}
