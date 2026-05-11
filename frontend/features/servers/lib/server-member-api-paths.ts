export function getServerMemberRolePath(
  serverId: string,
  membershipId: number,
): string {
  return `/servers/${serverId}/members/${membershipId}/role`;
}

export function getServerOwnershipTransferPath(serverId: string): string {
  return `/servers/${serverId}/ownership-transfer`;
}
