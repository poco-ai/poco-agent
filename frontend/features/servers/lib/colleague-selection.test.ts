import assert from "node:assert/strict";
import test from "node:test";

import { getExplicitColleagueSelection } from "./colleague-selection.ts";

test("returns the explicit colleague selection from the drawer", () => {
  assert.deepEqual(
    getExplicitColleagueSelection({
      type: "colleague",
      selection: { kind: "agent", id: "agent-1" },
    }),
    { kind: "agent", id: "agent-1" },
  );
});

test("does not infer a fallback colleague selection when the drawer is empty", () => {
  assert.equal(getExplicitColleagueSelection({ type: "none" }), null);
  assert.equal(
    getExplicitColleagueSelection({
      type: "colleague",
      selection: null,
    }),
    null,
  );
});
