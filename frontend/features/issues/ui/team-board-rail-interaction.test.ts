import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import test from "node:test";

const issuesPageSource = readFileSync(
  path.join(import.meta.dirname, "issues-pages.tsx"),
  "utf8",
);

test("board rail rows remain fully clickable for board switching", () => {
  assert.match(
    issuesPageSource,
    /onClick=\{\(\) => selectBoard\(board\.board_id\)\}/,
  );
});
