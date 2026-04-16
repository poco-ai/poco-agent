import test from "node:test";
import assert from "node:assert/strict";

import {
  buildTeamSectionHref,
  buildTeamSections,
} from "./team-sections.ts";

test("buildTeamSectionHref prefixes localized team routes", () => {
  assert.equal(buildTeamSectionHref("zh", "overview"), "/zh/team");
  assert.equal(buildTeamSectionHref("zh", "members"), "/zh/team/members");
  assert.equal(buildTeamSectionHref("zh", "invites"), "/zh/team/invites");
  assert.equal(buildTeamSectionHref("zh", "issues"), "/zh/team/issues");
});

test("buildTeamSectionHref falls back to non-localized team routes", () => {
  assert.equal(buildTeamSectionHref(undefined, "overview"), "/team");
  assert.equal(buildTeamSectionHref(undefined, "members"), "/team/members");
  assert.equal(buildTeamSectionHref(undefined, "invites"), "/team/invites");
  assert.equal(buildTeamSectionHref(undefined, "issues"), "/team/issues");
});

test("buildTeamSections returns team sections in navigation order", () => {
  assert.deepEqual(
    buildTeamSections("en").map((section) => section.id),
    ["overview", "members", "invites", "issues"],
  );
});
