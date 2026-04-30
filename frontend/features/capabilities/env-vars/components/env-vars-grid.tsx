"use client";

import * as React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  CircleOff,
  Loader2,
  Settings,
  Trash2,
  User,
  Wrench,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SkeletonShimmer } from "@/components/ui/skeleton-shimmer";
import { StaggeredList } from "@/components/ui/staggered-entrance";
import { useT } from "@/lib/i18n/client";
import type { EnvVar } from "@/features/capabilities/env-vars/types";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";

const EMPTY_ENV_VARS: EnvVar[] = [];

interface EnvVarsGridProps {
  envVars?: EnvVar[];
  savingKey?: string | null;
  isLoading?: boolean;
  onDelete?: (id: number) => void;
  onEdit?: (envVar: EnvVar) => void;
  onOverrideSystem?: (key: string) => void;
  onAddClick?: () => void;
}

function EnvVarsSection({
  title,
  icon,
  hint,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground/80 px-1">
        {icon}
        <span>{title}</span>
      </div>
      {hint ? (
        <p className="px-1 text-xs text-muted-foreground/80">{hint}</p>
      ) : null}
      <div className="space-y-4">{children}</div>
    </section>
  );
}

export function EnvVarsGrid({
  envVars: propEnvVars,
  savingKey,
  isLoading = false,
  onDelete,
  onEdit,
  onOverrideSystem,
  onAddClick,
}: EnvVarsGridProps) {
  const { t } = useT("translation");
  const hoverActionsClass =
    "flex items-center gap-2 transition-opacity md:opacity-0 md:pointer-events-none md:group-hover:opacity-100 md:group-hover:pointer-events-auto";
  const vars = propEnvVars?.length ? propEnvVars : EMPTY_ENV_VARS;

  const systemVars = React.useMemo(
    () => vars.filter((v) => v.scope === "system"),
    [vars],
  );
  const userVars = React.useMemo(
    () => vars.filter((v) => v.scope === "user"),
    [vars],
  );

  const systemKeys = React.useMemo(
    () => new Set(systemVars.map((v) => v.key)),
    [systemVars],
  );
  const userKeys = React.useMemo(
    () => new Set(userVars.map((v) => v.key)),
    [userVars],
  );

  return (
    <div className="space-y-6">
      <div className="rounded-xl bg-muted/50 px-5 py-3 flex flex-wrap items-center gap-3 md:flex-nowrap md:justify-between">
        <span className="text-sm text-muted-foreground">
          {t("library.envVars.scope.system")}: {systemVars.length} ·{" "}
          {t("library.envVars.scope.user")}: {userVars.length}
        </span>
      </div>
      <div className="space-y-3">
        {onAddClick ? (
          <CapabilityCreateCard
            label={t("library.envVars.header.add")}
            onClick={onAddClick}
          />
        ) : null}

        {isLoading && !vars.length ? (
          <SkeletonShimmer count={5} itemClassName="min-h-[64px]" gap="md" />
        ) : !vars.length ? (
          <div className="rounded-xl border border-border/50 bg-muted/10 px-4 py-6 text-sm text-muted-foreground text-center">
            {t("library.envVars.empty")}
          </div>
        ) : (
          <div className="space-y-8">
            {systemVars.length > 0 && (
              <EnvVarsSection
                title={t("library.envVars.scope.system")}
                icon={<Wrench className="size-4" />}
                hint={t("library.envVars.systemHint")}
              >
                <StaggeredList
                  items={systemVars}
                  show={!isLoading}
                  keyExtractor={(envVar) => envVar.id}
                  staggerDelay={50}
                  duration={400}
                  renderItem={(envVar) => {
                    const isOverridden = userKeys.has(envVar.key);
                    const isBusy = savingKey === envVar.key;
                    return (
                      <div className="flex items-center gap-4 rounded-xl border border-border/40 bg-muted/20 px-4 py-3 min-h-[64px]">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-sm">
                              {envVar.key}
                            </span>
                            <Badge
                              variant="outline"
                              className="text-xs text-muted-foreground"
                            >
                              {t("library.envVars.scope.system")}
                            </Badge>
                            {isOverridden && (
                              <Badge variant="secondary" className="text-xs">
                                {t("library.envVars.status.overridden")}
                              </Badge>
                            )}
                          </div>
                          {envVar.description && (
                            <p className="mt-1 text-xs text-muted-foreground break-words">
                              {envVar.description}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-3 flex-shrink-0">
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
                            onClick={() => onOverrideSystem?.(envVar.key)}
                            disabled={isBusy}
                          >
                            {isBusy ? (
                              <Loader2 className="size-4 animate-spin" />
                            ) : (
                              <User className="size-4" />
                            )}
                            {isOverridden
                              ? t("library.envVars.actions.editOverride")
                              : t("library.envVars.actions.override")}
                          </Button>
                          {envVar.is_set ? (
                            <span
                              title={t("library.envVars.status.set")}
                              className="shrink-0"
                            >
                              <CheckCircle2 className="size-4 text-primary" />
                            </span>
                          ) : (
                            <span
                              title={t("library.envVars.status.unset")}
                              className="shrink-0"
                            >
                              <CircleOff className="size-4 text-muted-foreground" />
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  }}
                />
              </EnvVarsSection>
            )}

            {userVars.length > 0 && (
              <EnvVarsSection
                title={t("library.envVars.scope.user")}
                icon={<User className="size-4" />}
                hint={t("library.envVars.userHint")}
              >
                <StaggeredList
                  items={userVars}
                  show={!isLoading}
                  keyExtractor={(envVar) => envVar.id}
                  staggerDelay={50}
                  duration={400}
                  renderItem={(envVar) => {
                    const overridesSystem = systemKeys.has(envVar.key);
                    const isBusy = savingKey === envVar.key;
                    return (
                      <div className="group flex items-center gap-4 rounded-xl border border-border/70 bg-card px-4 py-3 min-h-[64px]">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-sm">
                              {envVar.key}
                            </span>
                            <Badge
                              variant="outline"
                              className="text-xs text-muted-foreground"
                            >
                              {t("library.envVars.scope.user")}
                            </Badge>
                            {overridesSystem && (
                              <Badge variant="secondary" className="text-xs">
                                {t("library.envVars.status.overridesSystem")}
                              </Badge>
                            )}
                            {envVar.expose_to_runtime && (
                              <Badge
                                variant="outline"
                                className="text-xs border-amber-500/40 text-amber-700 dark:text-amber-300"
                              >
                                <AlertTriangle className="mr-1 size-3" />
                                {t("library.envVars.status.runtimeEnabled")}
                              </Badge>
                            )}
                          </div>
                          {envVar.description && (
                            <p className="mt-1 text-xs text-muted-foreground break-words">
                              {envVar.description}
                            </p>
                          )}
                        </div>

                        <div className="flex items-center gap-2 flex-shrink-0">
                          <div className={hoverActionsClass}>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8"
                              onClick={() => onEdit?.(envVar)}
                              disabled={isBusy}
                              title={t("common.edit")}
                            >
                              {isBusy ? (
                                <Loader2 className="size-4 animate-spin" />
                              ) : (
                                <Settings className="size-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="size-8 text-muted-foreground hover:text-destructive"
                              onClick={() => onDelete?.(envVar.id)}
                              title={t("common.delete")}
                              disabled={isBusy}
                            >
                              <Trash2 className="size-4" />
                            </Button>
                          </div>
                          <span
                            title={t("library.envVars.status.set")}
                            className="shrink-0"
                          >
                            <CheckCircle2 className="size-4 text-primary" />
                          </span>
                        </div>
                      </div>
                    );
                  }}
                />
              </EnvVarsSection>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
