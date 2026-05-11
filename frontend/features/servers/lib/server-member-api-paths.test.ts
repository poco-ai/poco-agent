import test from "node:test";
import assert from "node:assert/strict";

import {
  getServerMemberRolePath,
  getServerOwnershipTransferPath,
} from "./server-member-api-paths.ts";

test("getServerMemberRolePath returns the server member role endpoint", () => {
  assert.equal(
    getServerMemberRolePath("server-1", 42),
    "/servers/server-1/members/42/role",
  );
});

test("getServerOwnershipTransferPath returns the server ownership transfer endpoint", () => {
  assert.equal(
    getServerOwnershipTransferPath("server-1"),
    "/servers/server-1/ownership-transfer",
  );
});
