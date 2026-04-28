import test from "node:test";
import assert from "node:assert/strict";

import {
  getPresetGlyphVariantClassName,
  getPresetGlyphFrameClassName,
  getPresetGlyphImageClassName,
} from "./preset-visuals.ts";

test("getPresetGlyphVariantClassName returns stable layout classes per variant", () => {
  assert.match(getPresetGlyphVariantClassName("card"), /size-\[88px\]/);
  assert.match(getPresetGlyphVariantClassName("picker"), /size-10/);
  assert.match(getPresetGlyphVariantClassName("composer"), /size-7/);
  assert.match(getPresetGlyphVariantClassName("status"), /size-7/);
});

test("glyph frame and image helpers stay theme-neutral", () => {
  const frame = getPresetGlyphFrameClassName("card");
  const image = getPresetGlyphImageClassName("status");

  assert.match(frame, /border-border\/60/);
  assert.doesNotMatch(frame, /primary|#[0-9a-fA-F]{3,6}/);
  assert.match(image, /object-contain/);
  assert.match(image, /size-5/);
});
