import assert from "node:assert/strict";
import test from "node:test";

import { stringifyForDisplay } from "./generic-tool-viewer-utils.ts";

test("stringifyForDisplay always returns a string", () => {
  assert.equal(stringifyForDisplay(undefined), "");
  assert.equal(stringifyForDisplay("result"), "result");
  assert.equal(stringifyForDisplay(Symbol("result")), "Symbol(result)");
  assert.equal(stringifyForDisplay(() => null).startsWith("() =>"), true);
});

test("stringifyForDisplay keeps JSON formatting for serializable values", () => {
  assert.equal(
    stringifyForDisplay({ matches: ["src/app.tsx"] }),
    '{\n  "matches": [\n    "src/app.tsx"\n  ]\n}',
  );
});
