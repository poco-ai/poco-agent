"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

// loading pixel icon

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

const ICON_VARIANT_SWITCH_MS = 2200;
const ICON_FRAME_MS = 140;

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

interface PixelLoadingIconProps {
  className?: string;
}

export function PixelLoadingIcon({ className }: PixelLoadingIconProps) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const { variantIndex, frameIndex } = usePixelIconFrame(prefersReducedMotion);

  const litPixels = React.useMemo(() => {
    const variant = ICON_VARIANTS[variantIndex] ?? ICON_VARIANTS[0];
    const frame = variant[frameIndex % variant.length] ?? variant[0] ?? [];
    return new Set(frame);
  }, [frameIndex, variantIndex]);

  return (
    <span
      aria-hidden="true"
      className={cn("grid size-3.5 shrink-0 grid-cols-3 gap-[1px]", className)}
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
