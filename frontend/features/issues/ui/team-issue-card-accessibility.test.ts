import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

const issueCardSource = readFileSync(
  path.join(import.meta.dirname, "team-issue-card.tsx"),
  "utf8",
);

test("team issue card actions stay reachable beyond hover-only desktop interactions", () => {
  assert.match(
    issueCardSource,
    /className="flex items-center gap-0\.5 opacity-100 transition sm:opacity-0 sm:group-hover:opacity-100 sm:group-focus-within:opacity-100"/,
  );
});
