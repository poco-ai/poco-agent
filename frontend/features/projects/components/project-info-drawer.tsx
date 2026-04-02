"use client";

import * as React from "react";
import {
  CalendarClock,
  Files,
  GitBranch,
  Link2,
  MessageSquareText,
  PenSquare,
  Sparkles,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RenameProjectDialog } from "@/features/projects/components/rename-project-dialog";
import { ProjectFilesDialog } from "@/features/projects/components/project-files-dialog";
import { projectFilesService } from "@/features/projects/api/project-files-api";
import type { LocalMountConfig } from "@/features/chat/types/api/session";
import type { ProjectItem } from "@/features/projects/types";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

interface ProjectInfoDrawerProps {
  project: ProjectItem;
  sessionCount: number;
  presetCount: number;
  onUpdateProject: (updates: Partial<ProjectItem>) => Promise<void>;
  onOpenSettings: () => void;
  onDeleteProject?: () => Promise<void> | void;
}

interface QuickActionItem {
  key: string;
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  onClick?: () => void;
  badge?: number;
}

function formatUpdatedAt(updatedAt: string | undefined, locale: string) {
  if (!updatedAt) return null;
  const date = new Date(updatedAt);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date);
}

export function ProjectInfoDrawer({
  project,
  sessionCount,
  presetCount,
  onUpdateProject,
  onOpenSettings,
  onDeleteProject,
}: ProjectInfoDrawerProps) {
  const { t } = useT("translation");
  const lng = useLanguage() || "en";
  const [isRenameDialogOpen, setIsRenameDialogOpen] = React.useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [isFilesDialogOpen, setIsFilesDialogOpen] = React.useState(false);
  const [projectFilesCount, setProjectFilesCount] = React.useState(0);

  React.useEffect(() => {
    let active = true;

    const loadProjectFilesCount = async () => {
      try {
        const items = await projectFilesService.list(project.id, {
          revalidate: 0,
        });
        if (!active) return;
        setProjectFilesCount(items.length);
      } catch (error) {
        console.error(
          "[ProjectInfoDrawer] Failed to load project files",
          error,
        );
      }
    };

    void loadProjectFilesCount();
    return () => {
      active = false;
    };
  }, [project.id]);

  const updatedLabel =
    formatUpdatedAt(project.updatedAt, lng) ||
    t("project.detail.unknownUpdatedAt");
  const summary =
    project.description?.trim() || t("project.detail.emptyDescription");

  const stats = [
    {
      icon: MessageSquareText,
      label: t("project.detail.stats.sessions"),
      value: sessionCount.toString(),
    },
    {
      icon: Sparkles,
      label: t("project.detail.stats.presets"),
      value: presetCount.toString(),
    },
    {
      icon: CalendarClock,
      label: t("project.detail.stats.updated"),
      value: updatedLabel,
    },
  ];

  const quickActions: QuickActionItem[] = [
    {
      key: "presets",
      icon: Sparkles,
      title: t("project.detail.quickActions.presets.title"),
      onClick: onOpenSettings,
    },
    {
      key: "rename",
      icon: PenSquare,
      title: t("project.detail.quickActions.rename.title"),
      onClick: () => setIsRenameDialogOpen(true),
    },
    {
      key: "files",
      icon: Files,
      title: t("project.detail.quickActions.files.title"),
      onClick: () => setIsFilesDialogOpen(true),
      badge: projectFilesCount,
    },
  ];

  const handleRename = React.useCallback(
    (
      newName: string,
      newDescription?: string | null,
      defaultModel?: string | null,
      localMounts?: LocalMountConfig[],
    ) => {
      void onUpdateProject({
        name: newName,
        description: newDescription,
        defaultModel,
        localMounts,
      });
    },
    [onUpdateProject],
  );

  const handleDelete = React.useCallback(async () => {
    if (!onDeleteProject) return;
    try {
      setIsDeleting(true);
      await onDeleteProject();
    } finally {
      setIsDeleting(false);
      setIsDeleteDialogOpen(false);
    }
  }, [onDeleteProject]);

  return (
    <>
      <aside className="flex h-full w-72 shrink-0 flex-col bg-background">
        <div className="flex-1 overflow-y-auto px-4 pb-4 pt-4">
          <div className="space-y-1.5">
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {t("project.detail.overview")}
            </p>
            <p className="text-sm leading-6 text-muted-foreground">{summary}</p>
          </div>

          {project.repoUrl || project.gitBranch ? (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {project.repoUrl ? (
                <Badge
                  variant="outline"
                  className="max-w-[200px] gap-1.5 rounded-full border-border/70 bg-muted/30 px-2.5 py-0.5 text-xs text-muted-foreground"
                >
                  <Link2 className="size-3 shrink-0" />
                  <span className="truncate">{project.repoUrl}</span>
                </Badge>
              ) : null}
              {project.gitBranch ? (
                <Badge
                  variant="outline"
                  className="gap-1.5 rounded-full border-border/70 bg-muted/30 px-2.5 py-0.5 text-xs text-muted-foreground"
                >
                  <GitBranch className="size-3" />
                  <span>{project.gitBranch}</span>
                </Badge>
              ) : null}
            </div>
          ) : null}

          <div className="mt-5 space-y-2.5">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <div
                  key={stat.label}
                  className="flex items-center gap-2.5 text-sm"
                >
                  <Icon className="size-4 shrink-0 text-muted-foreground" />
                  <span className="text-muted-foreground">{stat.label}</span>
                  <span className="ml-auto font-medium text-foreground">
                    {stat.value}
                  </span>
                </div>
              );
            })}
          </div>

          <div className="my-4 border-t border-border/60" />

          <div className="space-y-1">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.16em] text-muted-foreground">
              {t("project.detail.quickActions.title")}
            </p>
            {quickActions.map((action) => {
              const Icon = action.icon;
              return (
                <Button
                  key={action.key}
                  variant="ghost"
                  className={cn(
                    "h-9 w-full justify-start gap-2.5 px-2 text-sm",
                  )}
                  onClick={action.onClick}
                >
                  <Icon className="size-4 text-primary" />
                  <span className="truncate">{action.title}</span>
                  {typeof action.badge === "number" ? (
                    <Badge
                      variant="outline"
                      className="ml-auto shrink-0 rounded-full border-border/70 bg-muted/40 px-1.5 py-0 text-[10px] text-muted-foreground"
                    >
                      {t("project.detail.files.count", { count: action.badge })}
                    </Badge>
                  ) : null}
                </Button>
              );
            })}
            {onDeleteProject ? (
              <Button
                variant="ghost"
                className="h-9 w-full justify-start gap-2.5 px-2 text-sm text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => setIsDeleteDialogOpen(true)}
              >
                <Trash2 className="size-4" />
                <span>{t("project.delete")}</span>
              </Button>
            ) : null}
          </div>
        </div>
      </aside>

      <RenameProjectDialog
        open={isRenameDialogOpen}
        onOpenChange={setIsRenameDialogOpen}
        projectName={project.name}
        projectDescription={project.description}
        projectDefaultModel={project.defaultModel}
        projectLocalMounts={project.localMounts}
        allowDescriptionEdit
        onRename={handleRename}
      />
      <AlertDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("project.delete")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("project.deleteDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel", "Cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={isDeleting}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("project.deleteConfirm", "Delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <ProjectFilesDialog
        open={isFilesDialogOpen}
        onOpenChange={setIsFilesDialogOpen}
        projectId={project.id}
        projectName={project.name}
        onFilesChange={(items) => setProjectFilesCount(items.length)}
      />
    </>
  );
}
