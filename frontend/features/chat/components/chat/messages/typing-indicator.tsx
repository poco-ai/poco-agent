"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";

const DEFAULT_TYPING_WORDS = [
  "Accomplishing",
  "Actioning",
  "Actualizing",
  "Baking",
  "Brewing",
  "Calculating",
  "Cerebrating",
  "Churning",
  "Clauding",
  "Coalescing",
  "Cogitating",
  "Computing",
  "Conjuring",
  "Considering",
  "Cooking",
  "Crafting",
  "Creating",
  "Crunching",
  "Deliberating",
  "Determining",
  "Doing",
  "Effecting",
  "Finagling",
  "Forging",
  "Forming",
  "Generating",
  "Hatching",
  "Herding",
  "Honking",
  "Hustling",
  "Ideating",
  "Inferring",
  "Manifesting",
  "Marinating",
  "Moseying",
  "Mulling",
  "Mustering",
  "Musing",
  "Noodling",
  "Percolating",
  "Pondering",
  "Processing",
  "Puttering",
  "Reticulating",
  "Ruminating",
  "Schlepping",
  "Shucking",
  "Simmering",
  "Smooshing",
  "Spinning",
  "Stewing",
  "Synthesizing",
  "Thinking",
  "Transmuting",
  "Vibing",
  "Working",
];

const TYPE_DELAY_MS = 70;
const DELETE_DELAY_MS = 40;
const WORD_HOLD_MS = 1400;
const WORD_SWITCH_PAUSE_MS = 320;
const ICON_VARIANT_SWITCH_MS = 2200;
const ICON_FRAME_MS = 140;

const ICON_VARIANTS: number[][][] = [
  // Twinkle star
  [
    [1, 3, 4, 5, 7],
    [0, 2, 4, 6, 8],
    [4],
    [3, 5],
    [1, 4, 7],
    [0, 4, 8],
    [2, 4, 6],
    [1, 3, 5, 7],
  ],
  // Orbit dot
  [[0], [1], [2], [5], [8], [7], [6], [3]],
  // Pulse cross
  [
    [4],
    [1, 3, 4, 5, 7],
    [0, 2, 4, 6, 8],
    [0, 1, 2, 3, 4, 5, 6, 7, 8],
    [0, 2, 4, 6, 8],
    [1, 3, 4, 5, 7],
  ],
  // Sweep bar
  [
    [0, 3, 6],
    [1, 4, 7],
    [2, 5, 8],
    [1, 4, 7],
    [0, 3, 6],
  ],
  // Corners + center
  [[0, 2, 6, 8], [1, 3, 5, 7], [4], [0, 2, 4, 6, 8], [1, 3, 4, 5, 7]],
  // Glitch shuffle
  [
    [0, 4, 8],
    [2, 4, 6],
    [0, 2, 5],
    [3, 4, 7],
    [1, 6, 8],
    [0, 5, 7],
    [2, 3, 8],
  ],
];

type IndicatorPhase = "typing" | "holding" | "deleting";

function isNonEmptyString(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function normalizeWords(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value.filter(isNonEmptyString);
}

function pickRandomWord(words: string[], previousWord: string | null): string {
  if (words.length === 0) return "Thinking";
  if (words.length === 1) return words[0];

  let nextWord = words[Math.floor(Math.random() * words.length)];
  while (nextWord === previousWord) {
    nextWord = words[Math.floor(Math.random() * words.length)];
  }
  return nextWord;
}

function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = React.useState(false);

  React.useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setPrefersReducedMotion(media.matches);

    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return prefersReducedMotion;
}

function usePixelIconFrame(prefersReducedMotion: boolean): {
  variantIndex: number;
  frameIndex: number;
} {
  const [variantIndex, setVariantIndex] = React.useState(0);
  const [frameIndex, setFrameIndex] = React.useState(0);

  React.useEffect(() => {
    if (prefersReducedMotion) return;

    const variantTimer = window.setInterval(() => {
      setVariantIndex((previous) => (previous + 1) % ICON_VARIANTS.length);
      setFrameIndex(0);
    }, ICON_VARIANT_SWITCH_MS);

    return () => window.clearInterval(variantTimer);
  }, [prefersReducedMotion]);

  React.useEffect(() => {
    if (prefersReducedMotion) return;

    const frameCount = ICON_VARIANTS[variantIndex]?.length ?? 1;
    const frameTimer = window.setInterval(() => {
      setFrameIndex((previous) => (previous + 1) % frameCount);
    }, ICON_FRAME_MS);

    return () => window.clearInterval(frameTimer);
  }, [prefersReducedMotion, variantIndex]);

  if (prefersReducedMotion) {
    return { variantIndex: 0, frameIndex: 0 };
  }

  return { variantIndex, frameIndex };
}

function PixelTypingIcon({
  variantIndex,
  frameIndex,
}: {
  variantIndex: number;
  frameIndex: number;
}) {
  const litPixels = React.useMemo(() => {
    const variant = ICON_VARIANTS[variantIndex] ?? ICON_VARIANTS[0];
    const frame = variant[frameIndex % variant.length] ?? variant[0] ?? [];
    return new Set(frame);
  }, [frameIndex, variantIndex]);

  return (
    <span
      aria-hidden="true"
      className="grid size-3.5 shrink-0 grid-cols-3 gap-[1px]"
    >
      {Array.from({ length: 9 }, (_, index) => (
        <span
          key={index}
          className={cn(
            "rounded-[1px] transition-all duration-100",
            litPixels.has(index)
              ? "bg-primary/90 opacity-100 scale-100"
              : "bg-primary/20 opacity-20 scale-[0.8]",
          )}
        />
      ))}
    </span>
  );
}

export function TypingIndicator() {
  const { t } = useT("translation");
  const prefersReducedMotion = usePrefersReducedMotion();
  const { variantIndex, frameIndex } = usePixelIconFrame(prefersReducedMotion);

  const configuredWords = React.useMemo(() => {
    const localizedWords = normalizeWords(
      t("chat.typingWords", { returnObjects: true }) as unknown,
    );
    return localizedWords.length > 0 ? localizedWords : DEFAULT_TYPING_WORDS;
  }, [t]);

  const [currentWord, setCurrentWord] = React.useState(() =>
    pickRandomWord(configuredWords, null),
  );
  const [displayText, setDisplayText] = React.useState("");
  const [phase, setPhase] = React.useState<IndicatorPhase>("typing");

  React.useEffect(() => {
    if (!configuredWords.includes(currentWord)) {
      setCurrentWord(pickRandomWord(configuredWords, currentWord));
      setDisplayText("");
      setPhase("typing");
    }
  }, [configuredWords, currentWord]);

  React.useEffect(() => {
    if (prefersReducedMotion) {
      setDisplayText(currentWord);
      return;
    }

    let timer: ReturnType<typeof setTimeout> | null = null;

    if (phase === "typing") {
      if (displayText.length < currentWord.length) {
        timer = setTimeout(() => {
          setDisplayText(currentWord.slice(0, displayText.length + 1));
        }, TYPE_DELAY_MS);
      } else {
        setPhase("holding");
      }
    } else if (phase === "holding") {
      timer = setTimeout(() => setPhase("deleting"), WORD_HOLD_MS);
    } else {
      if (displayText.length > 0) {
        timer = setTimeout(() => {
          setDisplayText((prev) => prev.slice(0, -1));
        }, DELETE_DELAY_MS);
      } else {
        timer = setTimeout(() => {
          setCurrentWord((previousWord) =>
            pickRandomWord(configuredWords, previousWord),
          );
          setPhase("typing");
        }, WORD_SWITCH_PAUSE_MS);
      }
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [configuredWords, currentWord, displayText, phase, prefersReducedMotion]);

  return (
    <div
      className="mt-2 flex h-5 items-center gap-2 text-sm text-muted-foreground"
      aria-live="polite"
    >
      <PixelTypingIcon variantIndex={variantIndex} frameIndex={frameIndex} />
      <span aria-hidden="true" className="font-mono tracking-tight">
        {displayText}
        <span className="ml-0.5 inline-block h-4 w-px bg-foreground/40 align-middle motion-safe:animate-pulse" />
      </span>
      <span className="sr-only">{t("chat.thinkingTitle")}</span>
    </div>
  );
}
