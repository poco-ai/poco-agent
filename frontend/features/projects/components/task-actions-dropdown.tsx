"use client";

import * as React from "react";
import { FolderPlus, Pencil, Pin, PinOff, Trash2 } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface TaskMenuProject {
  id: string;
  name: string;
}

interface TaskActionsDropdownProps {
  taskId: string;
  isPinned?: boolean;
  projects?: TaskMenuProject[];
  onTogglePin?: (taskId: string) => void | Promise<void>;
  onRename?: () => void;
  onMoveToProject?: (
    taskId: string,
    projectId: string | null,
  ) => void | Promise<void>;
  onDelete: (taskId: string) => void | Promise<void>;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  align?: "start" | "center" | "end";
  side?: "top" | "right" | "bottom" | "left";
  children: React.ReactNode;
}

export function TaskActionsDropdown({
  taskId,
  isPinned = false,
  projects = [],
  onTogglePin,
  onRename,
  onMoveToProject,
  onDelete,
  open,
  onOpenChange,
  align = "end",
  side,
  children,
}: TaskActionsDropdownProps) {
  const { t } = useT("translation");
  const canMoveToProject = Boolean(onMoveToProject) && projects.length > 0;

  return (
    <DropdownMenu open={open} onOpenChange={onOpenChange}>
      <DropdownMenuTrigger asChild>{children}</DropdownMenuTrigger>
      <DropdownMenuContent align={align} side={side}>
        {onTogglePin && (
          <DropdownMenuItem
            onClick={(event) => {
              event.stopPropagation();
              void onTogglePin(taskId);
            }}
          >
            {isPinned ? (
              <PinOff className="size-4" />
            ) : (
              <Pin className="size-4" />
            )}
            <span>{t(isPinned ? "sidebar.unpin" : "sidebar.pin")}</span>
          </DropdownMenuItem>
        )}

        {onRename && (
          <DropdownMenuItem
            onClick={(event) => {
              event.stopPropagation();
              onRename();
            }}
          >
            <Pencil className="size-4" />
            <span>{t("sidebar.rename")}</span>
          </DropdownMenuItem>
        )}

        {canMoveToProject ? (
          <DropdownMenuSub>
            <DropdownMenuSubTrigger className="focus:bg-muted focus:text-foreground data-[state=open]:bg-muted data-[state=open]:text-foreground">
              <FolderPlus className="size-4" />
              <span>{t("sidebar.moveToProject")}</span>
            </DropdownMenuSubTrigger>
            <DropdownMenuSubContent className="bg-popover">
              {projects.map((project) => (
                <DropdownMenuItem
                  key={project.id}
                  className="focus:bg-muted focus:text-foreground"
                  onClick={(event) => {
                    event.stopPropagation();
                    void onMoveToProject?.(taskId, project.id);
                  }}
                >
                  <span className="truncate">{project.name}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuSubContent>
          </DropdownMenuSub>
        ) : null}

        <DropdownMenuItem
          variant="destructive"
          onClick={(event) => {
            event.stopPropagation();
            void onDelete(taskId);
          }}
        >
          <Trash2 className="size-4 text-destructive" />
          <span>{t("sidebar.delete")}</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
