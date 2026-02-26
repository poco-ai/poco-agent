"use client";

import * as React from "react";
import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { setPendingCapabilityView } from "@/features/capabilities/lib/capability-view-state";
import type {
  ComposerMode,
  RepoUsageMode,
} from "@/features/task-composer/types";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function deriveProjectName(url: string): string {
  if (!url.trim()) return "";
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.toLowerCase();
    if (host !== "github.com" && host !== "www.github.com") return "";
    const parts = parsed.pathname.split("/").filter(Boolean);
    if (parts.length < 2) return "";
    const owner = parts[0];
    let repo = parts[1];
    if (repo.endsWith(".git")) repo = repo.slice(0, -4);
    return owner && repo ? `${owner}/${repo}` : "";
  } catch {
    return "";
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface RepoDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: ComposerMode;
  allowProjectize: boolean;
  lng?: string;
  /** Repo state (lifted from parent) */
  repoUrl: string;
  onRepoUrlChange: (url: string) => void;
  gitBranch: string;
  onGitBranchChange: (branch: string) => void;
  gitTokenEnvKey: string;
  onGitTokenEnvKeyChange: (key: string) => void;
  repoUsage: RepoUsageMode;
  onRepoUsageChange: (usage: RepoUsageMode) => void;
  projectName: string;
  onProjectNameChange: (name: string) => void;
  /** Called when user clicks Save */
  onSave: () => void;
}

/**
 * Dialog for configuring a GitHub repository to attach to a task.
 */
export function RepoDialog({
  open,
  onOpenChange,
  mode,
  allowProjectize,
  lng,
  repoUrl,
  onRepoUrlChange,
  gitBranch,
  onGitBranchChange,
  gitTokenEnvKey,
  onGitTokenEnvKeyChange,
  repoUsage,
  onRepoUsageChange,
  projectName,
  onProjectNameChange,
  onSave,
}: RepoDialogProps) {
  const { t } = useT("translation");

  const envVarsHref = React.useMemo(() => {
    const clean = (lng || "").trim();
    return clean ? `/${clean}/capabilities` : "/capabilities";
  }, [lng]);

  const handleOpenEnvVars = React.useCallback(() => {
    setPendingCapabilityView("env");
  }, []);

  const derivedName = React.useMemo(
    () => deriveProjectName(repoUrl),
    [repoUrl],
  );

  // Auto-fill project name when switching to create_project
  React.useEffect(() => {
    if (!allowProjectize || repoUsage !== "create_project") return;
    if (projectName.trim() || !derivedName) return;
    onProjectNameChange(derivedName);
  }, [
    allowProjectize,
    derivedName,
    onProjectNameChange,
    projectName,
    repoUsage,
  ]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>{t("hero.repo.dialogTitle")}</DialogTitle>
        </DialogHeader>

        <div className="grid gap-4 md:grid-cols-[7fr_3fr]">
          {/* URL */}
          <div className="space-y-2">
            <Label htmlFor="repo-url">{t("hero.repo.urlLabel")}</Label>
            <Input
              id="repo-url"
              value={repoUrl}
              onChange={(e) => onRepoUrlChange(e.target.value)}
              placeholder={t("hero.repo.urlPlaceholder")}
            />
          </div>

          {/* Branch */}
          <div className="space-y-2">
            <Label htmlFor="repo-branch">{t("hero.repo.branchLabel")}</Label>
            <Input
              id="repo-branch"
              value={gitBranch}
              onChange={(e) => onGitBranchChange(e.target.value)}
              placeholder={t("hero.repo.branchPlaceholder")}
            />
          </div>

          {/* Usage mode radio */}
          {allowProjectize && mode !== "scheduled" && (
            <div className="space-y-2 md:col-span-2">
              <Label>{t("hero.repo.usageLabel")}</Label>
              <RadioGroup
                value={repoUsage}
                onValueChange={(v) => onRepoUsageChange(v as RepoUsageMode)}
                className="gap-2"
              >
                <label className="flex items-start gap-3 rounded-lg border border-border bg-background px-3 py-2.5">
                  <RadioGroupItem value="session" className="mt-0.5" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-foreground">
                      {t("hero.repo.usage.session.title")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t("hero.repo.usage.session.help")}
                    </div>
                  </div>
                </label>

                <label className="flex items-start gap-3 rounded-lg border border-border bg-background px-3 py-2.5">
                  <RadioGroupItem value="create_project" className="mt-0.5" />
                  <div className="min-w-0">
                    <div className="text-sm font-medium text-foreground">
                      {t("hero.repo.usage.createProject.title")}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {t("hero.repo.usage.createProject.help")}
                    </div>
                  </div>
                </label>
              </RadioGroup>
            </div>
          )}

          {/* Project name */}
          {allowProjectize &&
            mode !== "scheduled" &&
            repoUsage === "create_project" && (
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="repo-project-name">
                  {t("hero.repo.projectNameLabel")}
                </Label>
                <Input
                  id="repo-project-name"
                  value={projectName}
                  onChange={(e) => onProjectNameChange(e.target.value)}
                  placeholder={t("hero.repo.projectNamePlaceholder")}
                />
              </div>
            )}

          {/* Token env key */}
          {repoUrl.trim() && (
            <div className="space-y-2 md:col-span-2">
              <div className="flex items-center justify-between gap-2">
                <Label htmlFor="repo-token-env-key">
                  {t("hero.repo.tokenKeyLabel")}
                </Label>
                <a
                  href={envVarsHref}
                  onClick={handleOpenEnvVars}
                  className="text-xs text-primary hover:underline"
                >
                  {t("hero.repo.goToEnvVars")}
                </a>
              </div>
              <Input
                id="repo-token-env-key"
                value={gitTokenEnvKey}
                onChange={(e) => onGitTokenEnvKeyChange(e.target.value)}
                placeholder={t("hero.repo.tokenKeyPlaceholder")}
              />
              <p className="text-xs text-muted-foreground">
                {t("hero.repo.tokenKeyHelp")}
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button type="button" onClick={onSave}>
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
