import test from "node:test";
import assert from "node:assert/strict";

import {
  canEditServerMemberRole,
  canRemoveServerMember,
  canShowTransferServerOwnershipAction,
  canTransferServerOwnership,
  getInvitedByDisplay,
  isServerRole,
} from "./server-member-permissions.ts";
import type { ServerMemberItem } from "../model/types.ts";

function member(overrides: Partial<ServerMemberItem>): ServerMemberItem {
  return {
    id: 1,
    serverId: "server-1",
    userId: "user-1",
    user: null,
    role: "member",
    joinedAt: "2026-05-10T00:00:00.000Z",
    invitedBy: null,
    status: "active",
    createdAt: "2026-05-10T00:00:00.000Z",
    updatedAt: "2026-05-10T00:00:00.000Z",
    ...overrides,
  };
}

test("isServerRole accepts only known server roles", () => {
  assert.equal(isServerRole("owner"), true);
  assert.equal(isServerRole("admin"), true);
  assert.equal(isServerRole("member"), true);
  assert.equal(isServerRole("guest"), false);
});

test("owner can edit non-owner member roles", () => {
  assert.equal(
    canEditServerMemberRole({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember: member({ userId: "member-user", role: "member" }),
    }),
    true,
  );
});

test("admin and member cannot edit other server member roles", () => {
  const targetMember = member({ userId: "member-user", role: "member" });

  assert.equal(
    canEditServerMemberRole({
      currentUserId: "admin-user",
      currentUserRole: "admin",
      targetMember,
    }),
    false,
  );
  assert.equal(
    canEditServerMemberRole({
      currentUserId: "member-user-2",
      currentUserRole: "member",
      targetMember,
    }),
    false,
  );
});

test("owner cannot directly edit owner roles or their own role", () => {
  assert.equal(
    canEditServerMemberRole({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember: member({ userId: "owner-user", role: "owner" }),
    }),
    false,
  );
  assert.equal(
    canEditServerMemberRole({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember: member({ userId: "other-owner", role: "owner" }),
    }),
    false,
  );
});

test("only owner can remove non-owner server members", () => {
  const targetMember = member({ userId: "member-user", role: "member" });

  assert.equal(
    canRemoveServerMember({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember,
    }),
    true,
  );
  assert.equal(
    canRemoveServerMember({
      currentUserId: "admin-user",
      currentUserRole: "admin",
      targetMember,
    }),
    false,
  );
});



test("personal servers show but disable ownership transfer", () => {
  const targetMember = member({ userId: "member-user", role: "member" });

  assert.equal(
    canShowTransferServerOwnershipAction({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember,
    }),
    true,
  );
  assert.equal(
    canTransferServerOwnership({
      currentUserId: "owner-user",
      currentUserRole: "owner",
      targetMember,
      serverKind: "personal",
    }),
    false,
  );
});

test("getInvitedByDisplay prefers display name and keeps user id as secondary text", () => {
  const inviter = member({
    id: 7,
    userId: "inviter-user",
    user: { userId: "inviter-user", displayName: "Junhao Zhuo" },
  });
  const selected = member({ invitedBy: "inviter-user" });

  assert.deepEqual(getInvitedByDisplay(selected, [inviter]), {
    primary: "Junhao Zhuo",
    secondary: "inviter-user",
  });
});

test("getInvitedByDisplay falls back to the inviter id when no profile matches", () => {
  const selected = member({ invitedBy: "missing-user" });

  assert.deepEqual(getInvitedByDisplay(selected, []), {
    primary: "missing-user",
    secondary: null,
  });
});
