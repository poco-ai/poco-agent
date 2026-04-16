import test from "node:test";
import assert from "node:assert/strict";

import type { WorkspaceInvite } from "../model/types.ts";
import {
  countActiveInvites,
  getInviteState,
} from "./team-overview.ts";

function createInvite(
  overrides: Partial<WorkspaceInvite> = {},
): WorkspaceInvite {
  return {
    id: "invite-1",
    workspaceId: "workspace-1",
    token: "token-1",
    role: "member",
    expiresAt: "2026-04-20T09:00:00Z",
    createdBy: "user-1",
    maxUses: 1,
    usedCount: 0,
    revokedAt: null,
    createdAt: "2026-04-16T09:00:00Z",
    updatedAt: "2026-04-16T09:00:00Z",
    ...overrides,
  };
}

test("countActiveInvites only counts invites that are not revoked", () => {
  const invites = [
    createInvite({ id: "invite-1", revokedAt: null }),
    createInvite({ id: "invite-2", revokedAt: "2026-04-17T09:00:00Z" }),
    createInvite({ id: "invite-3", revokedAt: null }),
  ];

  assert.equal(countActiveInvites(invites), 2);
});

test("getInviteState prioritizes revoked before expiry", () => {
  assert.equal(
    getInviteState(
      createInvite({
        revokedAt: "2026-04-16T12:00:00Z",
        expiresAt: "2026-04-15T12:00:00Z",
      }),
      new Date("2026-04-16T13:00:00Z"),
    ),
    "revoked",
  );
});

test("getInviteState marks past-due invites as expired", () => {
  assert.equal(
    getInviteState(
      createInvite({ expiresAt: "2026-04-15T12:00:00Z" }),
      new Date("2026-04-16T13:00:00Z"),
    ),
    "expired",
  );
  assert.equal(
    getInviteState(
      createInvite({ expiresAt: "2026-04-17T12:00:00Z" }),
      new Date("2026-04-16T13:00:00Z"),
    ),
    "active",
  );
});
