"use client";

import * as React from "react";
import { useMotionValue, useSpring } from "motion/react";

interface CountUpProps {
  value: number;
  format?: (n: number) => string;
  className?: string;
}

/**
 * Animates a number from 0 (or previous value) to the target value.
 * Respects prefers-reduced-motion.
 */
export function CountUp({
  value,
  format = (n) => Math.round(n).toLocaleString(),
  className,
}: CountUpProps) {
  const ref = React.useRef<HTMLSpanElement>(null);
  const [reducedMotion, setReducedMotion] = React.useState(false);

  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, {
    damping: 25,
    stiffness: 100,
  });

  React.useEffect(() => {
    if (typeof window === "undefined") return;
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = () => setReducedMotion(mq.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  React.useEffect(() => {
    if (reducedMotion) {
      if (ref.current) ref.current.textContent = format(value);
      return;
    }
    motionValue.set(value);
  }, [value, motionValue, format, reducedMotion]);

  React.useEffect(() => {
    if (reducedMotion) return;
    const unsubscribe = spring.on("change", (latest) => {
      if (ref.current) {
        ref.current.textContent = format(latest);
      }
    });
    return unsubscribe;
  }, [spring, format, reducedMotion]);

  if (reducedMotion) {
    return (
      <span ref={ref} className={className}>
        {format(value)}
      </span>
    );
  }

  return (
    <span ref={ref} className={className} suppressHydrationWarning>
      {format(0)}
    </span>
  );
}
