"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";
import { ChevronLeft, Users } from "lucide-react";

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
import { PageHeaderShell } from "@/components/shared/page-header-shell";
import { useLanguage } from "@/hooks/use-language";
import { useT } from "@/lib/i18n/client";
import { formatWorkspaceKind } from "@/features/workspaces/lib/format";
import {
  buildTeamSectionHref,
  buildTeamSections,
  type TeamSectionId,
} from "@/features/workspaces/lib/team-sections";
import { useWorkspaceContext } from "@/features/workspaces/model/workspace-context";
import { TeamSectionRail } from "@/features/workspaces/ui/team-section-rail";

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

function resolveSectionFromPath(pathname: string): TeamSectionId {
  if (pathname.includes("/members")) return "members";
  if (pathname.includes("/issues")) return "issues";
  return "overview";
}

interface TeamLibraryShellProps {
  children: React.ReactNode;
}

export function TeamLibraryShell({ children }: TeamLibraryShellProps) {
  const { t } = useT("translation");
  const lng = useLanguage();
  const pathname = usePathname();
  const router = useRouter();
  const {
    workspaces,
    currentWorkspace,
    currentWorkspaceId,
    isLoading,
    selectWorkspace,
  } = useWorkspaceContext();
  const [createOpen, setCreateOpen] = React.useState(false);

  const activeSection = React.useMemo(
    () => resolveSectionFromPath(pathname),
    [pathname],
  );

  const isMobileDetail = React.useMemo(
    () => activeSection !== "overview",
    [activeSection],
  );

  const sections = React.useMemo(
    () =>
      buildTeamSections(lng, {
        overview: t("sidebar.team"),
        members: t("workspaces.pages.members.title"),
        issues: t("issues.title"),
      }),
    [lng, t],
  );

  const activeSectionMeta = React.useMemo(
    () => sections.find((s) => s.id === activeSection),
    [sections, activeSection],
  );

  const railHeader = currentWorkspace ? (
    <div className="min-w-0 flex-1">
      <p className="truncate text-sm font-medium text-foreground">
        {currentWorkspace.name}
      </p>
      <Badge variant="secondary" className="mt-0.5">
        {formatWorkspaceKind(t, currentWorkspace.kind)}
      </Badge>
    </div>
  ) : null;

  const handleSelectSection = React.useCallback(
    (sectionId: TeamSectionId) => {
      const href = buildTeamSectionHref(lng, sectionId);
      router.push(href);
    },
    [lng, router],
  );

  const handleMobileBack = React.useCallback(() => {
    router.push(buildTeamSectionHref(lng, "overview"));
  }, [lng, router]);

  const headerTitle = isMobileDetail
    ? (activeSectionMeta?.label ?? t("sidebar.team"))
    : t("sidebar.team");
  const headerSubtitle = isMobileDetail
    ? undefined
    : currentWorkspace
      ? t("workspaces.currentWorkspace", { name: currentWorkspace.name })
      : t("workspaces.noWorkspace");

  const mobileBackButton = isMobileDetail ? (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className="text-muted-foreground md:hidden"
      aria-label={t("workspaces.mobile.back")}
      title={t("workspaces.mobile.back")}
      onClick={handleMobileBack}
    >
      <ChevronLeft className="size-4" />
    </Button>
  ) : null;

  return (
    <>
      <PageHeaderShell
        mobileLeading={mobileBackButton ?? undefined}
        hideSidebarTrigger={isMobileDetail}
        left={
          <div className="min-w-0 flex items-center gap-3">
            <Users
              className="hidden size-5 text-muted-foreground md:block"
              aria-hidden="true"
            />
            <div className="min-w-0">
              <p className="text-base font-semibold leading-tight">
                {headerTitle}
              </p>
              <p className="text-xs text-muted-foreground">
                {headerSubtitle}
              </p>
            </div>
          </div>
        }
        right={
          <div className="flex items-center gap-2">
            <Select
              value={currentWorkspaceId ?? undefined}
              onValueChange={selectWorkspace}
              disabled={isLoading || workspaces.length === 0}
            >
              <SelectTrigger className="w-44">
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
              size="sm"
              onClick={() => setCreateOpen(true)}
            >
              {t("workspaces.create.action")}
            </Button>
          </div>
        }
      />

      {/* Desktop: sidebar + detail pane */}
      <div className="hidden min-h-0 flex-1 md:grid md:grid-cols-[240px_minmax(0,1fr)]">
        <TeamSectionRail
          sections={sections}
          activeSectionId={activeSection}
          onSelect={handleSelectSection}
          header={railHeader}
        />
        <main className="min-h-0 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Mobile: section list or detail */}
      <div className="flex min-h-0 flex-1 md:hidden">
        {isMobileDetail ? (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <div className="min-h-0 flex-1 overflow-y-auto">
              {children}
            </div>
          </div>
        ) : (
          <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
            <TeamSectionRail
              sections={sections}
              activeSectionId={activeSection}
              onSelect={handleSelectSection}
              header={railHeader}
              variant="mobile"
            />
          </div>
        )}
      </div>

      <CreateWorkspaceDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </>
  );
}
