"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

const MATH_SCALE_CSS_VAR = "--markdown-math-scale";
const MIN_MATH_SCALE = 0.45;

const scaleDisplayMath = (root: HTMLElement) => {
  const displays = root.querySelectorAll<HTMLElement>(".katex-display");

  displays.forEach((display) => {
    const formula = display.querySelector<HTMLElement>(".katex");
    if (!formula) {
      return;
    }

    // Reset first to measure natural width before applying a new scale.
    display.style.setProperty(MATH_SCALE_CSS_VAR, "1");

    const availableWidth = display.clientWidth;
    const formulaWidth = formula.scrollWidth;

    if (availableWidth <= 0 || formulaWidth <= 0) {
      return;
    }

    const scale = Math.min(
      1,
      Math.max(MIN_MATH_SCALE, availableWidth / formulaWidth),
    );
    display.style.setProperty(MATH_SCALE_CSS_VAR, scale.toFixed(4));
  });
};

export function AdaptiveMarkdown({
  children,
  className,
}: React.PropsWithChildren<{ className?: string }>) {
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    let animationFrame = 0;

    const scheduleScale = () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }

      animationFrame = requestAnimationFrame(() => {
        animationFrame = 0;
        scaleDisplayMath(container);
      });
    };

    const resizeObserver = new ResizeObserver(() => {
      scheduleScale();
    });

    const mutationObserver = new MutationObserver(() => {
      scheduleScale();
    });

    resizeObserver.observe(container);
    mutationObserver.observe(container, {
      childList: true,
      subtree: true,
      characterData: true,
    });

    scheduleScale();

    return () => {
      if (animationFrame) {
        cancelAnimationFrame(animationFrame);
      }
      resizeObserver.disconnect();
      mutationObserver.disconnect();
    };
  }, []);

  return (
    <div ref={containerRef} className={cn("adaptive-markdown", className)}>
      {children}
    </div>
  );
}
