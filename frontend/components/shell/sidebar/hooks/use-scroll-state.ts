import { useState, useEffect, useRef, type RefObject } from "react";

interface UseScrollStateResult {
  scrollAreaRef: RefObject<HTMLDivElement | null>;
  isContentScrolled: boolean;
}

/**
 * Hook to track scroll state of a ScrollArea component.
 * Returns true when content is scrolled (for border visibility).
 */
export function useScrollState(): UseScrollStateResult {
  const [isContentScrolled, setIsContentScrolled] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector<HTMLElement>(
      "[data-slot='scroll-area-viewport']",
    );
    if (!viewport) return;

    const handleViewportScroll = () => {
      setIsContentScrolled(viewport.scrollTop > 0);
    };

    handleViewportScroll();
    viewport.addEventListener("scroll", handleViewportScroll, {
      passive: true,
    });
    return () => {
      viewport.removeEventListener("scroll", handleViewportScroll);
    };
  }, []);

  return {
    scrollAreaRef,
    isContentScrolled,
  };
}
