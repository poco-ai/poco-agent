"use client";

import * as React from "react";
import { motion, AnimatePresence } from "motion/react";

function splitIntoGraphemes(text: string): string[] {
  if (typeof Intl !== "undefined" && Intl.Segmenter) {
    const segmenter = new Intl.Segmenter("und", { granularity: "grapheme" });
    return Array.from(segmenter.segment(text), (s) => s.segment);
  }
  return Array.from(text);
}

interface RotatingTextProps {
  text: string;
  transition?: {
    type?: "spring" | "tween";
    damping?: number;
    stiffness?: number;
    delay?: number;
  };
  staggerDuration?: number;
  staggerFrom?: "first" | "last";
  className?: string;
  charClassName?: string;
}

export function RotatingText({
  text,
  transition = { type: "spring", damping: 25, stiffness: 300 },
  staggerDuration = 0.03,
  staggerFrom = "first",
  className,
  charClassName,
}: RotatingTextProps) {
  const chars = React.useMemo(() => splitIntoGraphemes(text), [text]);

  const getStaggerDelay = React.useCallback(
    (index: number): number => {
      if (staggerFrom === "first") return index * staggerDuration;
      return (chars.length - 1 - index) * staggerDuration;
    },
    [chars.length, staggerFrom, staggerDuration],
  );

  return (
    <span className={className}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={text}
          className="inline-flex flex-nowrap whitespace-nowrap"
          initial={false}
          aria-hidden="true"
        >
          {chars.map((char, i) => (
            <motion.span
              key={`${i}-${char}`}
              initial={{ y: "100%", opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: "-120%", opacity: 0 }}
              transition={{
                type: "spring",
                damping: 28,
                stiffness: 400,
                ...transition,
                delay: getStaggerDelay(i),
              }}
              className={`inline-block ${charClassName ?? ""}`}
            >
              {char}
            </motion.span>
          ))}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
