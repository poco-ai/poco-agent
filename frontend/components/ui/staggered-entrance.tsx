"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface StaggeredEntranceProps {
  /**
   * Children elements to animate
   */
  children: React.ReactNode;
  /**
   * Delay between each item in milliseconds
   */
  staggerDelay?: number;
  /**
   * Base animation duration in milliseconds
   */
  duration?: number;
  /**
   * Custom className for the container
   */
  className?: string;
  /**
   * Whether to show the animation (useful for toggling when data loads)
   */
  show?: boolean;
}

/**
 * StaggeredEntrance - Animates children with staggered entrance effect
 *
 * Features:
 * - Elements slide in from left sequentially
 * - Smooth fade-in effect
 * - Customizable timing
 *
 * @example
 * <StaggeredEntrance show={!isLoading}>
 *   {items.map(item => <div key={item.id}>{item.name}</div>)}
 * </StaggeredEntrance>
 */
export function StaggeredEntrance({
  children,
  staggerDelay = 50,
  duration = 300,
  className,
  show = true,
}: StaggeredEntranceProps) {
  const childArray = React.Children.toArray(children);

  if (!show) {
    return null;
  }

  return (
    <>
      {childArray.map((child, index) => (
        <div
          key={index}
          style={{
            animationDelay: `${index * staggerDelay}ms`,
            animationDuration: `${duration}ms`,
            animationFillMode: "both",
          }}
          className={cn("animate-in fade-in slide-in-from-left-3", className)}
        >
          {child}
        </div>
      ))}
    </>
  );
}

interface StaggeredListProps<T> {
  /**
   * Array of items to render
   */
  items: T[];
  /**
   * Render function for each item
   */
  renderItem: (item: T, index: number) => React.ReactNode;
  /**
   * Key extractor function
   */
  keyExtractor: (item: T, index: number) => string | number;
  /**
   * Delay between each item in milliseconds
   */
  staggerDelay?: number;
  /**
   * Base animation duration in milliseconds
   */
  duration?: number;
  /**
   * Custom className for each item wrapper
   */
  itemClassName?: string;
  /**
   * Custom className for the container
   */
  className?: string;
  /**
   * Whether to show the animation
   */
  show?: boolean;
}

/**
 * StaggeredList - Type-safe list component with staggered entrance animation
 *
 * @example
 * <StaggeredList
 *   items={skills}
 *   show={!isLoading}
 *   keyExtractor={(skill) => skill.id}
 *   renderItem={(skill) => <SkillCard skill={skill} />}
 * />
 */
export function StaggeredList<T>({
  items,
  renderItem,
  keyExtractor,
  staggerDelay = 50,
  duration = 300,
  itemClassName,
  className,
  show = true,
}: StaggeredListProps<T>) {
  if (!show) {
    return null;
  }

  return (
    <div className={cn("space-y-3", className)}>
      {items.map((item, index) => (
        <div
          key={keyExtractor(item, index)}
          style={{
            animationDelay: `${index * staggerDelay}ms`,
            animationDuration: `${duration}ms`,
            animationFillMode: "both",
          }}
          className={cn(
            "animate-in fade-in slide-in-from-left-3",
            itemClassName,
          )}
        >
          {renderItem(item, index)}
        </div>
      ))}
    </div>
  );
}
