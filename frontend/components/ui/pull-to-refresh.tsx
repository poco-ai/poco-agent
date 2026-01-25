"use client";

import { motion, useSpring, useTransform } from "motion/react";
import { useState, useRef } from "react";
import { ArrowDown, RefreshCw } from "lucide-react";

interface PullToRefreshProps {
  onRefresh: () => Promise<void>;
  children: React.ReactNode;
  threshold?: number;
  isLoading?: boolean;
}

export function PullToRefresh({
  onRefresh,
  children,
  threshold = 80,
  isLoading: externalLoading = false,
}: PullToRefreshProps) {
  const [, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isThresholdMet, setIsThresholdMet] = useState(false);
  const pullDistanceRef = useRef(0);

  const pullDistanceSpring = useSpring(0, {
    damping: 20,
    stiffness: 150,
  });

  const contentRef = useRef<HTMLDivElement>(null);
  const isGlobalLoading = externalLoading || isRefreshing;

  const handleTouchStart = (e: React.TouchEvent | React.MouseEvent) => {
    // Only allow pull to refresh if we're at the top of the container
    if (contentRef.current && contentRef.current.scrollTop > 0) return;

    const startY = "touches" in e ? e.touches[0].clientY : e.clientY;

    const handleMove = (moveEvent: TouchEvent | MouseEvent) => {
      const currentY =
        "touches" in moveEvent
          ? moveEvent.touches[0].clientY
          : moveEvent.clientY;
      const diff = currentY - startY;

      if (diff > 0) {
        // Apply resistance
        const distance = Math.min(diff * 0.4, threshold * 1.5);
        pullDistanceRef.current = distance;
        setPullDistance(distance);
        pullDistanceSpring.set(distance);

        const isMet = distance >= threshold;
        if (isMet && !isThresholdMet) {
          // Trigger subtle haptic feedback when crossing threshold
          if (typeof window !== "undefined" && "vibrate" in navigator) {
            navigator.vibrate(10);
          }
        }
        setIsThresholdMet(isMet);
      }
    };

    const handleEnd = async () => {
      window.removeEventListener("touchmove", handleMove);
      window.removeEventListener("mousemove", handleMove);
      window.removeEventListener("touchend", handleEnd);
      window.removeEventListener("mouseup", handleEnd);

      const finalDistance = pullDistanceRef.current;

      // Critical: Reset the ref immediately to avoid stale state in next touch
      pullDistanceRef.current = 0;

      if (finalDistance >= threshold) {
        // Trigger double vibration for refresh start
        if (typeof window !== "undefined" && "vibrate" in navigator) {
          navigator.vibrate([10, 30, 10]);
        }
        setIsRefreshing(true);
        pullDistanceSpring.set(60); // Keep it visible during refresh
        try {
          await onRefresh();
        } finally {
          setIsRefreshing(false);
          setPullDistance(0);
          pullDistanceSpring.set(0);
          setIsThresholdMet(false);
        }
      } else {
        setPullDistance(0);
        pullDistanceSpring.set(0);
        setIsThresholdMet(false);
      }
    };

    window.addEventListener("touchmove", handleMove);
    window.addEventListener("mousemove", handleMove);
    window.addEventListener("touchend", handleEnd);
    window.addEventListener("mouseup", handleEnd);
  };

  const opacity = useTransform(pullDistanceSpring, [0, threshold], [0, 1]);
  const scale = useTransform(pullDistanceSpring, [0, threshold], [0.8, 1]);

  return (
    <div
      className="relative flex flex-col flex-1 overflow-hidden h-full"
      onMouseDown={handleTouchStart}
      onTouchStart={handleTouchStart}
    >
      {/* Global Loading Bar at the very top */}
      <div className="absolute top-0 left-0 right-0 z-50 h-0.5 overflow-hidden">
        {isGlobalLoading && (
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: "100%" }}
            transition={{
              repeat: Infinity,
              duration: 1.5,
              ease: "linear",
            }}
            className="h-full w-1/2"
            style={{
              background:
                "linear-gradient(90deg, transparent, currentColor, transparent)",
            }}
          />
        )}
      </div>

      <motion.div
        style={{
          height: pullDistanceSpring,
          opacity,
          scale,
        }}
        className="absolute top-0 left-0 right-0 flex items-center justify-center overflow-hidden pointer-events-none"
      >
        <div className="flex flex-col items-center gap-1.5 pt-4">
          <motion.div
            animate={
              isRefreshing
                ? { rotate: 360 }
                : { rotate: isThresholdMet ? 180 : 0 }
            }
            transition={
              isRefreshing
                ? { repeat: Infinity, duration: 1, ease: "linear" }
                : { duration: 0.2 }
            }
            className={`p-2 rounded-full border shadow-sm transition-colors ${
              isThresholdMet
                ? "bg-muted text-foreground border-muted-foreground/20"
                : "bg-background text-muted-foreground border-border"
            }`}
          >
            {isRefreshing ? (
              <RefreshCw className="size-5" />
            ) : (
              <ArrowDown className="size-5" />
            )}
          </motion.div>

          <span
            className={`text-xs font-medium transition-colors ${
              isThresholdMet ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {isRefreshing
              ? "正在刷新..."
              : isThresholdMet
                ? "释放立即刷新"
                : "下拉刷新"}
          </span>
        </div>
      </motion.div>

      <motion.div
        ref={contentRef}
        style={{
          y: pullDistanceSpring,
        }}
        className="flex flex-1 flex-col overflow-auto select-none"
      >
        {children}
      </motion.div>
    </div>
  );
}
