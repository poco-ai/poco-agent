import type { ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export interface BaseCardProps {
  /** Icon element to display in the left slot */
  icon: ReactNode;
  /** Primary title text */
  title: string;
  /** Optional title tooltip */
  titleTooltip?: string;
  /** Secondary subtitle text */
  subtitle?: string;
  /** Optional subtitle tooltip */
  subtitleTooltip?: string;
  /** Click handler - makes the card clickable when provided */
  onClick?: () => void;
  /** Remove button handler */
  onRemove?: () => void;
  /** Whether to show the remove button (defaults to true when onRemove is provided) */
  showRemove?: boolean;
  /** Additional container classes */
  className?: string;
}

/**
 * Base card component for displaying items with icon, title, subtitle, and optional remove button.
 *
 * Provides a consistent layout and styling for file cards, repo cards, and similar UI elements.
 */
export function BaseCard({
  icon,
  title,
  titleTooltip,
  subtitle,
  subtitleTooltip,
  onClick,
  onRemove,
  showRemove = Boolean(onRemove),
  className,
}: BaseCardProps) {
  const isClickable = Boolean(onClick);

  return (
    <div
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onClick={isClickable ? onClick : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onClick?.();
              }
            }
          : undefined
      }
      className={cn(
        "group relative flex items-center gap-2 rounded-lg border border-border bg-card p-2 text-sm shadow-sm transition-all hover:shadow-md",
        isClickable ? "cursor-pointer" : "",
        className,
      )}
      title={subtitleTooltip}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        {icon}
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <p
          className="truncate font-medium text-foreground"
          title={titleTooltip ?? title}
        >
          {title}
        </p>
        {subtitle && (
          <p
            className="truncate text-xs text-muted-foreground"
            title={subtitleTooltip}
          >
            {subtitle}
          </p>
        )}
      </div>

      {showRemove && onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute -right-2 -top-2 hidden size-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm transition-opacity group-hover:flex hover:bg-destructive/90"
          type="button"
        >
          <X className="size-3" />
        </button>
      )}
    </div>
  );
}
