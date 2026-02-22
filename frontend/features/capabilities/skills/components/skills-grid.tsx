"use client";

import * as React from "react";
import { Trash2, PowerOff, AlertTriangle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { SkeletonShimmer } from "@/components/ui/skeleton-shimmer";
import { StaggeredList } from "@/components/ui/staggered-entrance";
import type {
  Skill,
  UserSkillInstall,
} from "@/features/capabilities/skills/types";
import { useT } from "@/lib/i18n/client";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";
import { CapabilitySourceAvatar } from "@/features/capabilities/components/capability-source-avatar";

const SKILL_LIMIT = 5;

interface SkillsGridProps {
  skills: Skill[];
  installs: UserSkillInstall[];
  loadingId?: number | null;
  isLoading?: boolean;
  onInstall?: (skillId: number) => void;
  onDeleteSkill?: (skillId: number) => void;
  onToggleEnabled?: (installId: number, enabled: boolean) => void;
  onBatchToggle?: (enabled: boolean) => void;
  createCardLabel?: string;
  onCreate?: () => void;
  toolbarSlot?: React.ReactNode;
}

export function SkillsGrid({
  skills,
  installs,
  loadingId,
  isLoading = false,
  onInstall,
  onDeleteSkill,
  onToggleEnabled,
  onBatchToggle,
  createCardLabel,
  onCreate,
  toolbarSlot,
}: SkillsGridProps) {
  const { t } = useT("translation");
  const actionIconClass =
    "rounded-lg transition-opacity md:opacity-0 md:pointer-events-none md:group-hover:opacity-100 md:group-hover:pointer-events-auto";

  const installBySkillId = React.useMemo(() => {
    const map = new Map<number, UserSkillInstall>();
    for (const install of installs) {
      map.set(install.skill_id, install);
    }
    return map;
  }, [installs]);

  const enabledCount = installs.filter((i) => i.enabled).length;

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
          {installs.length > 0 && (
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
          <StaggeredList
            items={skills}
            show={!isLoading}
            keyExtractor={(skill) => skill.id}
            staggerDelay={50}
            duration={400}
            renderItem={(skill) => {
              const install = installBySkillId.get(skill.id);
              const isInstalled = Boolean(install);
              const isRowLoading =
                isLoading ||
                loadingId === skill.id ||
                loadingId === install?.id;
              const isEnabled = install?.enabled ?? false;
              const avatarStatus =
                enabledCount > SKILL_LIMIT && isEnabled
                  ? "error"
                  : isEnabled
                    ? "active"
                    : "inactive";

              return (
                <div
                  className={`group flex items-center gap-4 rounded-xl border px-4 py-3 min-h-[64px] ${
                    isInstalled
                      ? "border-border/70 bg-card"
                      : "border-border/40 bg-muted/20"
                  }`}
                >
                  <CapabilitySourceAvatar
                    name={skill.name}
                    source={skill.source}
                    status={avatarStatus}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-medium truncate">{skill.name}</span>
                      <Badge
                        variant="outline"
                        className="text-xs text-muted-foreground"
                      >
                        {skill.scope === "system"
                          ? t("library.skillsManager.scope.system")
                          : t("library.skillsManager.scope.user")}
                      </Badge>
                    </div>
                  </div>

                  {isInstalled && install ? (
                    <div className="flex items-center gap-2">
                      {skill.scope === "user" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={isRowLoading}
                          onClick={() => onDeleteSkill?.(skill.id)}
                          className={actionIconClass}
                          title={t("common.delete")}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      )}
                      <Switch
                        checked={install.enabled}
                        disabled={isRowLoading}
                        onCheckedChange={(enabled) =>
                          onToggleEnabled?.(install.id, enabled)
                        }
                      />
                    </div>
                  ) : (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        disabled={isRowLoading}
                        onClick={() => onInstall?.(skill.id)}
                      >
                        {t("library.skillsManager.actions.install")}
                      </Button>
                      {skill.scope === "user" && (
                        <Button
                          variant="ghost"
                          size="icon"
                          disabled={isRowLoading}
                          onClick={() => onDeleteSkill?.(skill.id)}
                          className={actionIconClass}
                          title={t("common.delete")}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              );
            }}
          />
        )}
      </div>
    </div>
  );
}
