"use client";

import * as React from "react";
import { useT } from "@/lib/i18n/client";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Folder } from "lucide-react";

interface Project {
  id: string;
  name: string;
}

interface MoveTaskToProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projects: Project[];
  onMove: (projectId: string | null) => void;
}

/**
 * Dialog for moving a task to a project
 */
export function MoveTaskToProjectDialog({
  open,
  onOpenChange,
  projects,
  onMove,
}: MoveTaskToProjectDialogProps) {
  const { t } = useT("translation");
  const [selectedProjectId, setSelectedProjectId] = React.useState<
    string | null
  >(null);

  // Reset selection when dialog opens
  React.useEffect(() => {
    if (open) {
      setSelectedProjectId(null);
    }
  }, [open]);

  const handleMove = () => {
    onMove(selectedProjectId);
    onOpenChange(false);
  };

  const handleCancel = () => {
    setSelectedProjectId(null);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>{t("sidebar.moveToProject")}</DialogTitle>
          <DialogDescription>
            {t("projectDialogs.selectProject")}
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <ScrollArea className="max-h-[200px]">
            <div className="space-y-1 pr-4">
              {/* "No project" option (remove task-project association). */}
              <button
                type="button"
                onClick={() => setSelectedProjectId(null)}
                className={`
                  w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm
                  transition-colors
                  ${
                    selectedProjectId === null
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted"
                  }
                `}
              >
                <Folder className="size-4 shrink-0" />
                <span>{t("projectDialogs.noProject")}</span>
              </button>

              {/* Project list */}
              {projects.map((project) => (
                <button
                  key={project.id}
                  type="button"
                  onClick={() => setSelectedProjectId(project.id)}
                  className={`
                    w-full flex items-center gap-3 px-3 py-2 rounded-lg text-left text-sm
                    transition-colors
                    ${
                      selectedProjectId === project.id
                        ? "bg-primary text-primary-foreground"
                        : "hover:bg-muted"
                    }
                  `}
                >
                  <Folder className="size-4 shrink-0" />
                  <span className="flex-1 truncate">{project.name}</span>
                </button>
              ))}
            </div>
          </ScrollArea>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleCancel}>
            {t("projectDialogs.cancel")}
          </Button>
          <Button type="button" onClick={handleMove}>
            {t("projectDialogs.move")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
