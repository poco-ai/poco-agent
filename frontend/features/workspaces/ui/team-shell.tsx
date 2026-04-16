"use client";

import * as React from "react";
import Link from "next/link";

import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { buildTeamSections, type TeamSectionId } from "@/features/workspaces/lib/team-sections";
import { formatWorkspaceKind } from "@/features/workspaces/lib/format";
import { useWorkspaceContext } from "@/features/workspaces/model/workspace-context";

interface CreateWorkspaceDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

function CreateWorkspaceDialog({
  open,
  onOpenChange,
}: CreateWorkspaceDialogProps) {
  const { t } = useT("translation");
  const { createWorkspace } = useWorkspaceContext();
  const [name, setName] = React.useState("");
  const [isCreating, setIsCreating] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setName("");
      setIsCreating(false);
    }
  }, [open]);

  const handleCreate = async () => {
    setIsCreating(true);
    const created = await createWorkspace(name);
    setIsCreating(false);
    if (created) {
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("workspaces.create.dialogTitle")}</DialogTitle>
          <DialogDescription>
            {t("workspaces.create.dialogDescription")}
          </DialogDescription>
        </DialogHeader>
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder={t("workspaces.create.placeholder")}
          autoFocus
        />
        <DialogFooter>
          <Button
            type="button"
            onClick={() => void handleCreate()}
            disabled={isCreating || !name.trim()}
          >
            {t("workspaces.create.action")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

interface TeamShellProps {
  activePage: TeamSectionId;
  title: string;
  subtitle: string;
  headerActions?: React.ReactNode;
  toolbarActions?: React.ReactNode;
  children: React.ReactNode;
}

export function TeamShell({
  activePage,
  title,
  subtitle,
  headerActions,
  toolbarActions,
  children,
}: TeamShellProps) {
  const { t } = useT("translation");
  const lng = useLanguage();
  const {
    workspaces,
    currentWorkspace,
    currentWorkspaceId,
    isLoading,
    selectWorkspace,
  } = useWorkspaceContext();
  const [createOpen, setCreateOpen] = React.useState(false);

  const sections = React.useMemo(() => buildTeamSections(lng), [lng]);

  return (
    <>
      <PageHeaderShell
        left={
          <div className="min-w-0">
            <p className="truncate text-base font-semibold leading-tight text-foreground">
              {title}
            </p>
            <p className="truncate text-xs text-muted-foreground">{subtitle}</p>
          </div>
        }
        right={headerActions}
      />

      <main className="flex-1 overflow-auto p-4 sm:p-6">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-5">
          <section className="rounded-2xl border border-border/60 bg-card/80 p-4 shadow-sm">
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                <div className="min-w-0 space-y-2">
                  <div className="flex min-w-0 flex-wrap items-center gap-2">
                    <h2 className="truncate text-sm font-semibold text-foreground">
                      {currentWorkspace?.name ?? t("workspaces.noWorkspace")}
                    </h2>
                    {currentWorkspace ? (
                      <Badge variant="secondary">
                        {formatWorkspaceKind(t, currentWorkspace.kind)}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {currentWorkspace
                      ? t("workspaces.currentWorkspace", {
                          name: currentWorkspace.name,
                        })
                      : t("workspaces.noWorkspace")}
                  </p>
                </div>

                <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
                  <Select
                    value={currentWorkspaceId ?? undefined}
                    onValueChange={selectWorkspace}
                    disabled={isLoading || workspaces.length === 0}
                  >
                    <SelectTrigger className="w-full min-w-0 sm:w-56">
                      <SelectValue
                        placeholder={t("workspaces.switcher.placeholder")}
                      />
                    </SelectTrigger>
                    <SelectContent>
                      {workspaces.map((workspace) => (
                        <SelectItem key={workspace.id} value={workspace.id}>
                          {workspace.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>

                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setCreateOpen(true)}
                  >
                    {t("workspaces.create.action")}
                  </Button>
                </div>
              </div>

              <nav className="flex flex-wrap gap-2" aria-label={t("sidebar.team")}>
                {sections.map((section) => {
                  const label =
                    section.id === "issues"
                      ? t("issues.title")
                      : t(`workspaces.pages.${section.id}.title`);

                  return (
                    <Button
                      key={section.id}
                      asChild
                      size="sm"
                      variant={section.id === activePage ? "default" : "outline"}
                      className={cn(
                        "rounded-full",
                        section.id === activePage && "shadow-sm",
                      )}
                    >
                      <Link href={section.href}>{label}</Link>
                    </Button>
                  );
                })}
              </nav>

              {toolbarActions ? (
                <div className="flex flex-wrap items-center gap-2 border-t border-border/60 pt-4">
                  {toolbarActions}
                </div>
              ) : null}
            </div>
          </section>

          {children}
        </div>
      </main>

      <CreateWorkspaceDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </>
  );
}
