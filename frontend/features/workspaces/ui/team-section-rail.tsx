"use client";

import * as React from "react";

import { cn } from "@/lib/utils";
import type { TeamSection, TeamSectionId } from "@/features/workspaces/lib/team-sections";

interface TeamSectionRailProps {
  sections: TeamSection[];
  activeSectionId: TeamSectionId;
  onSelect?: (sectionId: TeamSectionId) => void;
  variant?: "default" | "mobile";
  header?: React.ReactNode;
}

export function TeamSectionRail({
  sections,
  activeSectionId,
  onSelect,
  variant = "default",
  header,
}: TeamSectionRailProps) {
  const isMobile = variant === "mobile";

  const handleClick = React.useCallback(
    (sectionId: TeamSectionId) => {
      onSelect?.(sectionId);
    },
    [onSelect],
  );

  const verticalNavClassName = isMobile
    ? "flex flex-1 flex-col gap-1 overflow-y-auto px-4 py-4"
    : "hidden flex-1 overflow-y-auto px-2 pb-2 pt-5 md:flex md:flex-col";

  return (
    <aside
      className={cn(
        "flex min-h-0 flex-col border-b border-border/50 md:border-b-0 md:border-r md:border-border/50",
        isMobile && "h-full",
      )}
    >
      {!isMobile ? (
        <div className="flex gap-4 overflow-x-auto px-4 py-2 md:hidden">
          {sections.map((section) => {
            const isActive = section.id === activeSectionId;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => handleClick(section.id)}
                className={cn(
                  "flex items-center gap-1.5 whitespace-nowrap rounded-md px-2 py-2 text-sm font-serif",
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
              >
                <span className="truncate font-medium">{section.label}</span>
              </button>
            );
          })}
        </div>
      ) : null}

      <nav className={verticalNavClassName}>
        {header ? (
          <div className="mb-3 flex items-center gap-2 px-3">
            {header}
          </div>
        ) : null}
        <div className="space-y-1">
          {sections.map((section) => {
            const isActive = section.id === activeSectionId;
            return (
              <button
                key={section.id}
                type="button"
                onClick={() => handleClick(section.id)}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm font-serif",
                  isActive
                    ? "bg-muted text-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
                aria-current={isActive ? "true" : undefined}
              >
                {section.icon ? (
                  <section.icon className="size-4 shrink-0" />
                ) : null}
                <span className="truncate font-medium">{section.label}</span>
              </button>
            );
          })}
        </div>
      </nav>
    </aside>
  );
}
