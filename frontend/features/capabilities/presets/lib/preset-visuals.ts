export type PresetGlyphVariant = "card" | "picker" | "composer" | "status";

const GLYPH_VARIANT_CLASS_NAMES: Record<PresetGlyphVariant, string> = {
  card: "size-[88px] rounded-[28px]",
  picker: "size-10 rounded-xl",
  composer: "size-7 rounded-lg",
  status: "size-7 rounded-xl",
};

const GLYPH_IMAGE_CLASS_NAMES: Record<PresetGlyphVariant, string> = {
  card: "size-[68px]",
  picker: "size-7",
  composer: "size-5",
  status: "size-5",
};

export function getPresetGlyphVariantClassName(
  variant: PresetGlyphVariant,
): string {
  return GLYPH_VARIANT_CLASS_NAMES[variant];
}

export function getPresetGlyphFrameClassName(
  variant: PresetGlyphVariant,
): string {
  return [
    "flex shrink-0 items-center justify-center overflow-hidden border border-border/60 bg-muted/[0.36] text-foreground",
    GLYPH_VARIANT_CLASS_NAMES[variant],
  ].join(" ");
}

export function getPresetGlyphImageClassName(
  variant: PresetGlyphVariant,
): string {
  return [
    "shrink-0 object-contain object-center",
    GLYPH_IMAGE_CLASS_NAMES[variant],
  ].join(" ");
}
