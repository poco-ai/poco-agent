import type { ComposerMode } from "@/features/task-composer/types";

export const COMPOSER_MODE_SEQUENCE: readonly ComposerMode[] = [
  "task",
  "plan",
  "scheduled",
] as const;

function getModeIndex(mode: ComposerMode) {
  return COMPOSER_MODE_SEQUENCE.indexOf(mode);
}

export function getNextComposerMode(mode: ComposerMode): ComposerMode {
  const idx = getModeIndex(mode);
  if (idx === -1) return COMPOSER_MODE_SEQUENCE[0];
  return COMPOSER_MODE_SEQUENCE[(idx + 1) % COMPOSER_MODE_SEQUENCE.length];
}

export function getPreviousComposerMode(mode: ComposerMode): ComposerMode {
  const idx = getModeIndex(mode);
  if (idx === -1) return COMPOSER_MODE_SEQUENCE[0];
  const nextIdx =
    (idx - 1 + COMPOSER_MODE_SEQUENCE.length) % COMPOSER_MODE_SEQUENCE.length;
  return COMPOSER_MODE_SEQUENCE[nextIdx];
}
