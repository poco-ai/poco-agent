"use client";

import * as React from "react";
import { FolderKanban, GitBranch, Link2, PenSquare } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RenameProjectDialog } from "@/features/projects/components/rename-project-dialog";
import type { ProjectItem } from "@/features/projects/types";
import { useT } from "@/lib/i18n/client";

interface ProjectInfoHeaderProps {
  project: ProjectItem;
  onUpdate: (updates: Partial<ProjectItem>) => Promise<void>;
  renameSignal?: number;
}

export function ProjectInfoHeader({
  project,
  onUpdate,
  renameSignal = 0,
}: ProjectInfoHeaderProps) {
  const { t } = useT("translation");
  const [isRenameDialogOpen, setIsRenameDialogOpen] = React.useState(false);

  React.useEffect(() => {
    if (renameSignal === 0) return;
    setIsRenameDialogOpen(true);
  }, [renameSignal]);

  const handleRename = React.useCallback(
    async (name: string) => {
      await onUpdate({ name });
    },
    [onUpdate],
  );

  const summary =
    project.description?.trim() ||
    project.repoUrl?.trim() ||
    t("project.detail.emptyDescription");

  return (
    <>
      <section className="rounded-3xl border border-border/60 bg-background px-5 py-5 shadow-sm sm:px-6">
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="flex min-w-0 items-start gap-4">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                <FolderKanban className="size-6" />
              </div>
              <div className="min-w-0 space-y-2">
                <Badge
                  variant="outline"
                  className="rounded-full border-border/70 bg-muted/40 px-2.5 py-1 text-[11px] font-medium text-muted-foreground"
                >
                  {t("project.detail.overview")}
                </Badge>
                <div className="space-y-1">
                  <h1 className="truncate text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">
                    {project.name}
                  </h1>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {summary}
                  </p>
                </div>
              </div>
            </div>

            <Button
              variant="outline"
              className="shrink-0"
              onClick={() => setIsRenameDialogOpen(true)}
            >
              <PenSquare className="size-4" />
              {t("project.detail.renameAction")}
            </Button>
          </div>

          <div className="flex flex-wrap gap-2">
            {project.repoUrl ? (
              <Badge
                variant="outline"
                className="max-w-full gap-1.5 rounded-full border-border/70 bg-muted/30 px-3 py-1 text-muted-foreground"
              >
                <Link2 className="size-3.5" />
                <span className="truncate">{project.repoUrl}</span>
              </Badge>
            ) : null}
            {project.gitBranch ? (
              <Badge
                variant="outline"
                className="gap-1.5 rounded-full border-border/70 bg-muted/30 px-3 py-1 text-muted-foreground"
              >
                <GitBranch className="size-3.5" />
                <span>{project.gitBranch}</span>
              </Badge>
            ) : null}
          </div>
        </div>
      </section>

      <RenameProjectDialog
        open={isRenameDialogOpen}
        onOpenChange={setIsRenameDialogOpen}
        projectName={project.name}
        onRename={(name) => {
          void handleRename(name);
        }}
      />
    </>
  );
}
