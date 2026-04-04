"use client";

import * as React from "react";
import { FolderKanban, PanelLeftClose } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import type { ProjectItem } from "@/features/projects/types";
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { cn } from "@/lib/utils";

interface ProjectHeaderProps {
  project?: ProjectItem;
  isDrawerOpen?: boolean;
  onToggleDrawer?: () => void;
  onOpenSettings?: () => void;
}

export function ProjectHeader({
  project,
  isDrawerOpen,
  onToggleDrawer,
}: ProjectHeaderProps) {
  const { t } = useT("translation");

  if (isDrawerOpen) {
    return (
      <PageHeaderShell
        sticky={false}
        hideSidebarTrigger
        className="border-b-0 pt-[8px]"
        left={
          <div className="flex min-w-0 items-center gap-1.5">
            <FolderKanban className="size-4 shrink-0 text-primary" />
            <span className="truncate text-sm font-medium text-foreground">
              {project?.name ?? t("project.untitled", "Untitled Project")}
            </span>
          </div>
        }
        right={
          <Button
            variant="ghost"
            size="icon"
            className="size-8 text-muted-foreground hover:bg-muted"
            onClick={onToggleDrawer}
            aria-label={t("chat.collapse")}
            title={t("chat.collapse")}
          >
            <PanelLeftClose className="size-4" />
          </Button>
        }
      />
    );
  }

  return (
    <PageHeaderShell
      className="border-b-0 pt-[8px]"
      left={
        <div className="flex min-w-0 items-center gap-2">
          <button
            type="button"
            className={cn(
              "inline-flex min-w-0 items-center gap-1.5 rounded-md px-2 py-1 text-left text-sm text-foreground transition-colors hover:bg-accent hover:text-accent-foreground",
            )}
            onClick={onToggleDrawer}
          >
            <FolderKanban className="size-4 shrink-0 text-primary" />
            <span className="truncate font-medium text-foreground">
              {project?.name ?? t("project.untitled", "Untitled Project")}
            </span>
          </button>
        </div>
      }
    />
  );
}
