"use client";

import * as React from "react";
import {
  Trash2,
  PowerOff,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SkeletonShimmer } from "@/components/ui/skeleton-shimmer";
import type {
  Skill,
  UserSkillInstall,
} from "@/features/capabilities/skills/types";
import { getEffectiveInstallState } from "@/features/capabilities/lib/install-policy";
import type { SourceInfo } from "@/features/capabilities/types/source";
import { formatSourceLabel } from "@/features/capabilities/utils/source";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";
import { CapabilitySourceAvatar } from "@/features/capabilities/components/capability-source-avatar";

const SKILL_LIMIT = 5;

interface SkillsGridProps {
  skills: Skill[];
  installs: UserSkillInstall[];
  loadingId?: number | null;
  isLoading?: boolean;
  displayMode?: "personal" | "runtime" | "admin";
  onInstall?: (skillId: number, enabled?: boolean) => void;
  onDeleteSkill?: (skillId: number) => void;
  onOpenSkillSettings?: (skill: Skill) => void;
  onToggleEnabled?: (installId: number, enabled: boolean) => void;
  onBatchToggle?: (enabled: boolean) => void;
  createCardLabel?: string;
  onCreate?: () => void;
  toolbarSlot?: React.ReactNode;
}

interface CustomSkillGroup {
  key: string;
  title: string;
  source: SourceInfo | null;
  skills: Skill[];
}

export function SkillsGrid({
  skills,
  installs,
  loadingId,
  isLoading = false,
  displayMode = "personal",
  onInstall,
  onDeleteSkill,
  onOpenSkillSettings,
  onToggleEnabled,
  onBatchToggle,
  createCardLabel,
  onCreate,
  toolbarSlot,
}: SkillsGridProps) {
  const { t } = useT("translation");
  const [collapsedGroupKeys, setCollapsedGroupKeys] = React.useState<
    Set<string>
  >(() => new Set());
  const actionIconClass = "rounded-lg transition-opacity";

  const installBySkillId = React.useMemo(() => {
    const map = new Map<number, UserSkillInstall>();
    for (const install of installs) {
      map.set(install.skill_id, install);
    }
    return map;
  }, [installs]);
  const systemSkills = React.useMemo(
    () => skills.filter((skill) => skill.scope === "system"),
    [skills],
  );
  const userSkills = React.useMemo(
    () => skills.filter((skill) => skill.scope !== "system"),
    [skills],
  );
  const marketSkills = React.useMemo(
    () => userSkills.filter((skill) => skill.source?.kind === "marketplace"),
    [userSkills],
  );
  const customSkills = React.useMemo(
    () => userSkills.filter((skill) => skill.source?.kind !== "marketplace"),
    [userSkills],
  );

  const customSkillGroups = React.useMemo<CustomSkillGroup[]>(() => {
    const groups = new Map<string, CustomSkillGroup>();

    for (const skill of customSkills) {
      const sourceKind = skill.source?.kind ?? "unknown";
      const sourceLabel = formatSourceLabel(skill.source, t);
      const sourceRepo = skill.source?.repo?.trim();
      const title =
        sourceKind === "github"
          ? sourceRepo
            ? sourceRepo
            : sourceLabel
          : sourceLabel;

      const key = [
        sourceKind,
        skill.source?.repo?.trim().toLowerCase() ?? "",
        skill.source?.url?.trim().toLowerCase() ?? "",
        skill.source?.ref?.trim().toLowerCase() ?? "",
        skill.source?.filename?.trim().toLowerCase() ?? "",
        skill.source?.market?.trim().toLowerCase() ?? "",
        sourceLabel.trim().toLowerCase(),
      ].join("|");

      const existingGroup = groups.get(key);
      if (existingGroup) {
        existingGroup.skills.push(skill);
        continue;
      }

      groups.set(key, {
        key: `custom:${key}`,
        title,
        source: skill.source ?? null,
        skills: [skill],
      });
    }

    return Array.from(groups.values())
      .map((group) => ({
        ...group,
        skills: [...group.skills].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      }))
      .sort((left, right) => left.title.localeCompare(right.title));
  }, [customSkills, t]);

  const marketSkillGroups = React.useMemo<CustomSkillGroup[]>(() => {
    const groups = new Map<string, CustomSkillGroup>();

    for (const skill of marketSkills) {
      const repo = skill.source?.repo?.trim();
      const fallbackLabel = formatSourceLabel(skill.source, t);
      const title = repo || fallbackLabel;
      const key = (repo || fallbackLabel).trim().toLowerCase();

      const existingGroup = groups.get(key);
      if (existingGroup) {
        existingGroup.skills.push(skill);
        continue;
      }

      groups.set(key, {
        key: `marketplace:${key}`,
        title,
        source: skill.source ?? null,
        skills: [skill],
      });
    }

    return Array.from(groups.values())
      .map((group) => ({
        ...group,
        skills: [...group.skills].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      }))
      .sort((left, right) => left.title.localeCompare(right.title));
  }, [marketSkills, t]);

  const systemSkillGroups = React.useMemo<CustomSkillGroup[]>(() => {
    if (systemSkills.length === 0) return [];
    return [
      {
        key: "system:system",
        title: t("library.skillsManager.sections.system"),
        source: { kind: "system" },
        skills: [...systemSkills].sort((left, right) =>
          left.name.localeCompare(right.name),
        ),
      },
    ];
  }, [systemSkills, t]);

  const allSkillGroups = React.useMemo<CustomSkillGroup[]>(
    () => [...systemSkillGroups, ...marketSkillGroups, ...customSkillGroups],
    [customSkillGroups, marketSkillGroups, systemSkillGroups],
  );

  const visibleSkillGroups = React.useMemo(() => {
    if (displayMode === "admin") {
      return systemSkillGroups;
    }
    if (displayMode === "personal") {
      return [...marketSkillGroups, ...customSkillGroups];
    }
    return allSkillGroups;
  }, [
    allSkillGroups,
    customSkillGroups,
    displayMode,
    marketSkillGroups,
    systemSkillGroups,
  ]);
  const enabledCount = React.useMemo(
    () =>
      skills.reduce((count, skill) => {
        const install = installBySkillId.get(skill.id);
        return (
          count + (getEffectiveInstallState(skill, install).isEnabled ? 1 : 0)
        );
      }, 0),
    [installBySkillId, skills],
  );

  function SkillRow({ skill }: { skill: Skill }) {
    const [isHovered, setIsHovered] = React.useState(false);
    const install = installBySkillId.get(skill.id);
    const isBuiltin = skill.scope === "system";
    const isAgentCreated =
      skill.scope === "user" && skill.source?.kind === "skill-creator";
    const isMarketplace = skill.source?.kind === "marketplace";
    const categoryLabel = isBuiltin
      ? t("library.skillsManager.sections.system")
      : isMarketplace
        ? t("library.sources.marketplace")
        : t("library.skillsManager.sections.custom");
    const installState = getEffectiveInstallState(skill, install);
    const hasInstall = installState.hasInstall;
    const isInstalled = installState.isInstalled;
    const isRowLoading =
      isLoading || loadingId === skill.id || loadingId === install?.id;
    const showDeleteAction = isHovered;

    return (
      <div className="min-h-[64px]">
        <div
          className={`flex min-h-[64px] items-center rounded-xl border px-4 py-3 ${
            isInstalled
              ? "border-border/70 bg-card"
              : "border-border/40 bg-muted/20"
          }`}
          onPointerEnter={() => setIsHovered(true)}
          onPointerLeave={() => setIsHovered(false)}
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => onOpenSkillSettings?.(skill)}
                disabled={!onOpenSkillSettings}
                className={cn(
                  "max-w-full truncate text-left font-medium underline underline-offset-4 decoration-transparent transition-[color,text-decoration-color] duration-300 ease-out",
                  onOpenSkillSettings
                    ? "cursor-pointer hover:decoration-muted-foreground/30"
                    : "cursor-default",
                )}
              >
                {skill.name}
              </button>
              <Badge
                variant="outline"
                className="text-xs text-muted-foreground"
              >
                {categoryLabel}
              </Badge>
              {skill.default_enabled && !skill.force_enabled ? (
                <Badge variant="secondary" className="text-xs">
                  {t("common.default")}
                </Badge>
              ) : null}
              {skill.force_enabled ? (
                <Badge variant="destructive" className="text-xs">
                  {t("common.forced")}
                </Badge>
              ) : null}
              {isAgentCreated && (
                <Badge variant="secondary" className="text-xs">
                  {t("library.skillsManager.source.skillCreator")}
                </Badge>
              )}
            </div>
            {skill.description ? (
              <p className="mt-0.5 truncate text-xs text-muted-foreground">
                {skill.description}
              </p>
            ) : null}
          </div>

          {displayMode === "admin" && isBuiltin && onDeleteSkill ? (
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                disabled={isRowLoading}
                onClick={() => onDeleteSkill?.(skill.id)}
                className={cn(
                  actionIconClass,
                  showDeleteAction
                    ? "opacity-100 pointer-events-auto"
                    : "opacity-0 pointer-events-none",
                )}
                title={t("common.delete")}
              >
                <Trash2 className="size-4" />
              </Button>
            </div>
          ) : isInstalled ? (
            <div className="flex items-center gap-2">
              {skill.scope === "user" && (
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={isRowLoading}
                  onClick={() => onDeleteSkill?.(skill.id)}
                  className={cn(
                    actionIconClass,
                    showDeleteAction
                      ? "opacity-100 pointer-events-auto"
                      : "opacity-0 pointer-events-none",
                  )}
                  title={t("common.delete")}
                >
                  <Trash2 className="size-4" />
                </Button>
              )}
              {displayMode === "admin" ? null : (
                <Switch
                  checked={installState.isEnabled}
                  disabled={isRowLoading || skill.force_enabled}
                  onCheckedChange={(enabled) =>
                    install
                      ? onToggleEnabled?.(install.id, enabled)
                      : onInstall?.(skill.id, enabled)
                  }
                />
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                disabled={isRowLoading}
                onClick={() => onInstall?.(skill.id)}
              >
                {skill.default_enabled || skill.force_enabled
                  ? t("common.enabled")
                  : t("library.skillsManager.actions.install")}
              </Button>
              {skill.scope === "user" && (
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={isRowLoading}
                  onClick={() => onDeleteSkill?.(skill.id)}
                  className={cn(
                    actionIconClass,
                    showDeleteAction
                      ? "opacity-100 pointer-events-auto"
                      : "opacity-0 pointer-events-none",
                  )}
                  title={t("common.delete")}
                >
                  <Trash2 className="size-4" />
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    );
  }

  const renderSkillRow = (skill: Skill, key?: React.Key) => (
    <SkillRow key={key ?? skill.id} skill={skill} />
  );

  const renderSourceTree = (groups: CustomSkillGroup[]) => {
    if (groups.length === 0) {
      return null;
    }

    return (
      <div className="space-y-3">
        <div className="relative pl-0">
          <div className="space-y-0">
            {groups.map((group, index) => (
              <div
                key={group.key}
                className={cn(
                  "group/repo relative",
                  index < groups.length - 1 ? "pb-6" : null,
                )}
              >
                {index > 0 ? (
                  <span
                    aria-hidden="true"
                    className="absolute left-6 top-0 h-6 w-px bg-border/70"
                  />
                ) : null}
                {index < groups.length - 1 ? (
                  <span
                    aria-hidden="true"
                    className="absolute bottom-0 left-6 top-6 w-px bg-border/70"
                  />
                ) : null}
                {(() => {
                  const fullGroupKey = group.key;
                  const isCollapsed = collapsedGroupKeys.has(fullGroupKey);

                  return (
                    <>
                      <button
                        type="button"
                        onClick={() => {
                          setCollapsedGroupKeys((prev) => {
                            const next = new Set(prev);
                            if (next.has(fullGroupKey)) {
                              next.delete(fullGroupKey);
                            } else {
                              next.add(fullGroupKey);
                            }
                            return next;
                          });
                        }}
                        className="flex w-full items-center gap-3 rounded-xl border border-transparent py-2 pl-2 pr-3 text-left"
                        aria-expanded={!isCollapsed}
                      >
                        <CapabilitySourceAvatar
                          name={group.title}
                          source={group.source}
                          className="size-8 shrink-0 bg-card [&>svg]:size-4"
                          statusDotClassName="hidden"
                        />
                        <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground md:text-base">
                          {group.title}
                        </span>
                        <span className="opacity-0 transition-opacity group-hover/repo:opacity-100 group-focus-within/repo:opacity-100">
                          {isCollapsed ? (
                            <ChevronRight className="size-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="size-4 text-muted-foreground" />
                          )}
                        </span>
                      </button>
                      {!isCollapsed ? (
                        <div className="mt-3 space-y-2 pl-16">
                          {group.skills.map((skill) =>
                            renderSkillRow(skill, skill.id),
                          )}
                        </div>
                      ) : null}
                    </>
                  );
                })()}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Warning alert */}
      {enabledCount > SKILL_LIMIT && (
        <Alert className="border-amber-500/50 bg-amber-500/10 text-amber-600 dark:text-amber-500 [&>svg]:text-amber-600 dark:[&>svg]:text-amber-500 *:data-[slot=alert-description]:text-amber-600/90 dark:*:data-[slot=alert-description]:text-amber-500/90">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            {t("hero.warnings.tooManySkills", { count: enabledCount })}
          </AlertDescription>
        </Alert>
      )}

      {/* Action bar */}
      <div className="rounded-xl bg-muted/50 px-5 py-3 flex flex-wrap items-center gap-3 md:flex-nowrap md:justify-between">
        <span className="text-sm text-muted-foreground">
          {t("library.skillsManager.stats.enabled")}: {enabledCount}
        </span>
        <div className="flex flex-1 flex-nowrap items-center justify-end gap-2 overflow-x-auto">
          {enabledCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onBatchToggle?.(false)}
              className="gap-2"
            >
              <PowerOff className="size-4" />
              {t("skillsGrid.turnOffAll")}
            </Button>
          )}
          {toolbarSlot}
        </div>
      </div>

      <div className="space-y-3">
        {createCardLabel ? (
          <CapabilityCreateCard label={createCardLabel} onClick={onCreate} />
        ) : null}

        {isLoading && skills.length === 0 ? (
          <SkeletonShimmer count={5} itemClassName="min-h-[64px]" gap="md" />
        ) : !isLoading && skills.length === 0 ? (
          <div className="rounded-xl border border-border/50 bg-muted/10 px-4 py-6 text-sm text-muted-foreground text-center">
            {t("library.skillsManager.empty")}
          </div>
        ) : (
          <div className="space-y-4">
            {renderSourceTree(visibleSkillGroups)}
          </div>
        )}
      </div>
    </div>
  );
}
