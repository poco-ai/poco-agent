import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

const contextBarSource = readFileSync(
  path.join(import.meta.dirname, "team-board-context-bar.tsx"),
  "utf8",
);
const issuesPageSource = readFileSync(
  path.join(import.meta.dirname, "issues-pages.tsx"),
  "utf8",
);

test("team issues page keeps a reachable board settings entry point", () => {
  assert.match(contextBarSource, /onOpenBoardSettings:\s*\(boardId: string\) => void/);
  assert.match(issuesPageSource, /onOpenBoardSettings=\{setBoardSettingsId\}/);
});
