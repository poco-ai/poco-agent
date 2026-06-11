import test from "node:test";
import assert from "node:assert/strict";

import {
  filterInputFileReferences,
  getInputFileReferenceCandidates,
  getInputFileReferenceTrigger,
  insertInputFileReference,
} from "./input-file-reference.ts";
import type { InputFile } from "@/features/chat/types/api/session";

const files: InputFile[] = [
  {
    id: "file-1",
    name: "design.pdf",
    source: "s3://bucket/design.pdf",
    size: 120,
    content_type: "application/pdf",
  },
  {
    id: "file-2",
    name: "notes.md",
    source: "s3://bucket/notes.md",
    size: 80,
    content_type: "text/markdown",
  },
  {
    id: "file-duplicate",
    name: "design.pdf",
    source: "s3://bucket/design.pdf",
    size: 120,
    content_type: "application/pdf",
  },
];

test("getInputFileReferenceTrigger detects current hash token only", () => {
  assert.deepEqual(getInputFileReferenceTrigger("check #des", 10), {
    start: 6,
    end: 10,
    query: "des",
  });
  assert.equal(getInputFileReferenceTrigger("check /run", 10), null);
  assert.equal(getInputFileReferenceTrigger("check #bad token", 16), null);
});

test("getInputFileReferenceCandidates filters by display name and dedupes source", () => {
  const candidates = getInputFileReferenceCandidates(files, "des");
  assert.equal(candidates.length, 1);
  assert.equal(candidates[0]?.displayName, "design.pdf");
  assert.equal(candidates[0]?.source, "s3://bucket/design.pdf");
});

test("insertInputFileReference replaces trigger with readable token", () => {
  const candidate = getInputFileReferenceCandidates(files, "des")[0];
  assert.ok(candidate);

  const result = insertInputFileReference("please read #des", 16, 16, candidate);
  assert.ok(result);
  assert.equal(result.value, "please read #design.pdf ");
  assert.equal(result.cursor, 24);
  assert.equal(result.reference.insertedText, "#design.pdf");
  assert.deepEqual(result.reference.range, { start: 12, end: 23 });
});

test("filterInputFileReferences removes deleted tokens and missing files", () => {
  const candidate = getInputFileReferenceCandidates(files, "des")[0];
  assert.ok(candidate);
  const inserted = insertInputFileReference("read #des", 9, 9, candidate);
  assert.ok(inserted);

  assert.equal(
    filterInputFileReferences(
      [inserted.reference],
      "read #design.pdf",
      files,
    ).length,
    1,
  );
  assert.equal(
    filterInputFileReferences([inserted.reference], "read design.pdf", files)
      .length,
    0,
  );
  assert.equal(
    filterInputFileReferences([inserted.reference], inserted.value, [
      files[1] as InputFile,
    ]).length,
    0,
  );
});
