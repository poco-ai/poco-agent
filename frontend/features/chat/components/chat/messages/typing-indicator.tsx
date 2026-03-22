"use client";

import * as React from "react";
import { useT } from "@/lib/i18n/client";
import { PixelLoadingIcon } from "./pixel-loading-icon";

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

export function TypingIndicator() {
  const { t } = useT("translation");
  const prefersReducedMotion = usePrefersReducedMotion();

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
      <PixelLoadingIcon />
      <span aria-hidden="true" className="font-mono tracking-tight">
        {displayText}
        <span className="ml-0.5 inline-block h-4 w-px bg-foreground/40 align-middle motion-safe:animate-pulse" />
      </span>
      <span className="sr-only">{t("chat.thinkingTitle")}</span>
    </div>
  );
}
