"use client";

import * as React from "react";
import { CheckCircle2 } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

const MATH_SCALE_CSS_VAR = "--markdown-math-scale";
const MIN_MATH_SCALE = 0.45;
const MATH_COPIED_MS = 900;

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

const getMathSource = (element: Element) => {
  const annotation =
    element.querySelector<HTMLElement>(
      "annotation[encoding='application/x-tex']",
    ) ?? element.querySelector<HTMLElement>("annotation");

  const source = annotation?.textContent?.replace(/\u00a0/g, " ").trim();
  return source ? source : null;
};

const wrapFormulaWithDisplayMath = (source: string) => `$$\n${source}\n$$`;

type FormulaFeedback = {
  top: number;
  right: number;
};

export function AdaptiveMarkdown({
  children,
  className,
}: React.PropsWithChildren<{ className?: string }>) {
  const { t } = useT("translation");
  const containerRef = React.useRef<HTMLDivElement>(null);
  const copiedTimerRef = React.useRef<number | null>(null);
  const [feedback, setFeedback] = React.useState<FormulaFeedback | null>(null);

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

  React.useEffect(() => {
    return () => {
      if (copiedTimerRef.current) {
        window.clearTimeout(copiedTimerRef.current);
      }
    };
  }, []);

  const onMathClick = React.useCallback(
    async (event: React.MouseEvent<HTMLDivElement>) => {
      const target = event.target;
      if (!(target instanceof Element)) {
        return;
      }

      const formula = target.closest(".katex, .katex-display");
      if (!(formula instanceof HTMLElement)) {
        return;
      }

      const container = containerRef.current;
      if (!container || !container.contains(formula)) {
        return;
      }

      // Skip copy when user is selecting text.
      if (window.getSelection()?.toString()) {
        return;
      }

      const source = getMathSource(formula);
      if (!source) {
        return;
      }

      try {
        await navigator.clipboard.writeText(wrapFormulaWithDisplayMath(source));
      } catch (error) {
        console.error("[AdaptiveMarkdown] Copy formula failed", error);
        return;
      }

      const feedbackHost =
        formula.closest(".katex-display") instanceof HTMLElement
          ? (formula.closest(".katex-display") as HTMLElement)
          : formula;
      const hostRect = feedbackHost.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      setFeedback({
        top: hostRect.top - containerRect.top + hostRect.height / 2,
        right: containerRect.right - hostRect.right + 8,
      });

      if (copiedTimerRef.current) {
        window.clearTimeout(copiedTimerRef.current);
      }
      copiedTimerRef.current = window.setTimeout(() => {
        setFeedback(null);
        copiedTimerRef.current = null;
      }, MATH_COPIED_MS);
    },
    [],
  );

  return (
    <div
      ref={containerRef}
      onClick={onMathClick}
      className={cn(
        "adaptive-markdown relative [&_.katex]:cursor-copy [&_.katex-display]:cursor-copy",
        className,
      )}
    >
      {feedback && (
        <span
          className="pointer-events-none absolute z-10 -translate-y-1/2 inline-flex items-center gap-1 rounded-full border border-border/60 bg-background/95 px-2 py-1 text-xs text-foreground shadow-sm"
          style={{ top: feedback.top, right: feedback.right }}
        >
          <CheckCircle2 className="size-4 text-primary" />
          <span>{t("chat.formulaCopied")}</span>
        </span>
      )}
      {children}
    </div>
  );
}
