"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Plug, Server, Sparkles, X } from "lucide-react";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import type {
  McpServer,
  UserMcpInstall,
} from "@/features/capabilities/mcp/types";
import { Skill, UserSkillInstall } from "@/features/capabilities/skills/types";
import type {
  Plugin,
  UserPluginInstall,
} from "@/features/capabilities/plugins/types";
import { useAppShell } from "@/components/shell/app-shell-context";
import { cn } from "@/lib/utils";
import { playInstallSound } from "@/lib/utils/sound";
import { useT } from "@/lib/i18n/client";
import {
  getStartupPreloadValue,
  hasStartupPreloadValue,
  invalidateStartupPreloadValues,
} from "@/lib/startup-preload";
import { toast } from "sonner";
import { SkeletonText } from "@/components/ui/skeleton-shimmer";
import { StaggeredEntrance } from "@/components/ui/staggered-entrance";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const MCP_LIMIT = 3;
const SKILL_LIMIT = 5;

type CapabilityViewId = "mcp" | "skills" | "presets";

export interface CardNavProps {
  triggerText?: string;
  className?: string;
  embedded?: boolean;
  showDismiss?: boolean;
  onDismiss?: () => void;
}

interface InstalledItem {
  id: number;
  name: string;
  enabled: boolean;
  installId: number;
}

interface PreviewItem {
  id: string;
  name: string;
  type: "mcp" | "skill" | "plugin";
}

/**
 * CardNav Component
 *
 * Entry card that opens a dialog with MCP, Skill, and Preset controls
 */
export function CardNav({
  triggerText,
  className = "",
  embedded = false,
  showDismiss = false,
  onDismiss,
}: CardNavProps) {
  const router = useRouter();
  const { lng } = useAppShell();
  const { t } = useT("translation");
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  // Default trigger text from i18n if not provided
  const displayText = triggerText ?? t("cardNav.connectTools");
  const didInitialRefreshRef = useRef(false);

  const preloadMcpServers = getStartupPreloadValue("mcpServers");
  const preloadMcpInstalls = getStartupPreloadValue("mcpInstalls");
  const preloadSkills = getStartupPreloadValue("skills");
  const preloadSkillInstalls = getStartupPreloadValue("skillInstalls");
  const preloadPlugins = getStartupPreloadValue("plugins");
  const preloadPluginInstalls = getStartupPreloadValue("pluginInstalls");
  const hasPreloadedCardData =
    hasStartupPreloadValue("mcpServers") &&
    hasStartupPreloadValue("mcpInstalls") &&
    hasStartupPreloadValue("skills") &&
    hasStartupPreloadValue("skillInstalls") &&
    hasStartupPreloadValue("plugins") &&
    hasStartupPreloadValue("pluginInstalls");

  // API data state
  const [mcpServers, setMcpServers] = useState<McpServer[]>(
    hasPreloadedCardData ? (preloadMcpServers ?? []) : [],
  );
  const [mcpInstalls, setMcpInstalls] = useState<UserMcpInstall[]>(
    hasPreloadedCardData ? (preloadMcpInstalls ?? []) : [],
  );
  const [skills, setSkills] = useState<Skill[]>(
    hasPreloadedCardData ? (preloadSkills ?? []) : [],
  );
  const [skillInstalls, setSkillInstalls] = useState<UserSkillInstall[]>(
    hasPreloadedCardData ? (preloadSkillInstalls ?? []) : [],
  );
  const [plugins, setPlugins] = useState<Plugin[]>(
    hasPreloadedCardData ? (preloadPlugins ?? []) : [],
  );
  const [pluginInstalls, setPluginInstalls] = useState<UserPluginInstall[]>(
    hasPreloadedCardData ? (preloadPluginInstalls ?? []) : [],
  );
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(hasPreloadedCardData);
  const [hasFetchedFresh, setHasFetchedFresh] = useState(false);

  // Fetch MCP/Skill/Plugin data
  const fetchData = useCallback(
    async (force = false) => {
      if ((!force && hasFetchedFresh) || isLoading) return;

      setIsLoading(true);
      try {
        const [
          mcpServersData,
          mcpInstallsData,
          skillsData,
          skillInstallsData,
          pluginsData,
          pluginInstallsData,
        ] = await Promise.all([
          mcpService.listServers(),
          mcpService.listInstalls(),
          skillsService.listSkills(),
          skillsService.listInstalls(),
          pluginsService.listPlugins(),
          pluginsService.listInstalls(),
        ]);
        setMcpServers(mcpServersData);
        setMcpInstalls(mcpInstallsData);
        setSkills(skillsData);
        setSkillInstalls(skillInstallsData);
        setPlugins(pluginsData);
        setPluginInstalls(pluginInstallsData);
        setHasFetched(true);
        setHasFetchedFresh(true);
      } catch (error) {
        console.error("[CardNav] Failed to fetch data:", error);
      } finally {
        setIsLoading(false);
      }
    },
    [hasFetchedFresh, isLoading],
  );

  // Refresh once on mount to avoid stale startup-preload data after capability changes.
  useEffect(() => {
    if (didInitialRefreshRef.current) return;
    didInitialRefreshRef.current = true;
    void fetchData(true);
  }, [fetchData]);

  // Get all installed MCPs
  const installedMcps: InstalledItem[] = mcpInstalls.map((install) => {
    const server = mcpServers.find((s) => s.id === install.server_id);
    return {
      id: install.server_id,
      name: server?.name || t("cardNav.fallbackMcp", { id: install.server_id }),
      enabled: install.enabled,
      installId: install.id,
    };
  });

  // Get all installed Skills
  const installedSkills: InstalledItem[] = skillInstalls.map((install) => {
    const skill = skills.find((s) => s.id === install.skill_id);
    return {
      id: install.skill_id,
      name: skill?.name || t("cardNav.fallbackSkill", { id: install.skill_id }),
      enabled: install.enabled,
      installId: install.id,
    };
  });

  // Get all installed Plugins
  const installedPlugins: InstalledItem[] = pluginInstalls.map((install) => {
    const plugin = plugins.find((p) => p.id === install.plugin_id);
    return {
      id: install.plugin_id,
      name:
        plugin?.name || t("cardNav.fallbackPreset", { id: install.plugin_id }),
      enabled: install.enabled,
      installId: install.id,
    };
  });

  // Toggle MCP enabled state
  const toggleMcpEnabled = useCallback(
    async (installId: number, currentEnabled: boolean) => {
      // Check if enabling would exceed the limit
      const currentEnabledCount = mcpInstalls.filter((i) => i.enabled).length;
      if (!currentEnabled && currentEnabledCount >= MCP_LIMIT) {
        toast.warning(t("hero.warnings.mcpLimitReached"));
        return;
      }

      try {
        await mcpService.updateInstall(installId, { enabled: !currentEnabled });
        setMcpInstalls((prev) =>
          prev.map((install) =>
            install.id === installId
              ? { ...install, enabled: !currentEnabled }
              : install,
          ),
        );
        invalidateStartupPreloadValues(["mcpInstalls"]);
        if (!currentEnabled) {
          playInstallSound();
        }

        // Check if we've exceeded the limit after enabling
        const newEnabledCount = !currentEnabled
          ? currentEnabledCount + 1
          : currentEnabledCount;
        if (newEnabledCount > MCP_LIMIT) {
          toast.warning(
            t("hero.warnings.tooManyMcps", { count: newEnabledCount }),
          );
        }
      } catch (error) {
        console.error("[CardNav] Failed to toggle MCP:", error);
      }
    },
    [mcpInstalls, t],
  );

  // Toggle Skill enabled state
  const toggleSkillEnabled = useCallback(
    async (installId: number, currentEnabled: boolean) => {
      // Check if enabling would exceed the limit
      const currentEnabledCount = skillInstalls.filter((i) => i.enabled).length;
      if (!currentEnabled && currentEnabledCount >= SKILL_LIMIT) {
        toast.warning(t("hero.warnings.skillLimitReached"));
        return;
      }

      try {
        await skillsService.updateInstall(installId, {
          enabled: !currentEnabled,
        });
        setSkillInstalls((prev) =>
          prev.map((install) =>
            install.id === installId
              ? { ...install, enabled: !currentEnabled }
              : install,
          ),
        );
        invalidateStartupPreloadValues(["skillInstalls"]);
        if (!currentEnabled) {
          playInstallSound();
        }

        // Check if we've exceeded the limit after enabling
        const newEnabledCount = !currentEnabled
          ? currentEnabledCount + 1
          : currentEnabledCount;
        if (newEnabledCount > SKILL_LIMIT) {
          toast.warning(
            t("hero.warnings.tooManySkills", { count: newEnabledCount }),
          );
        }
      } catch (error) {
        console.error("[CardNav] Failed to toggle Skill:", error);
      }
    },
    [skillInstalls, t],
  );

  // Toggle Plugin enabled state
  const togglePluginEnabled = useCallback(
    async (installId: number, currentEnabled: boolean) => {
      const shouldEnable = !currentEnabled;
      const otherEnabledInstalls = pluginInstalls.filter(
        (install) => install.enabled && install.id !== installId,
      );
      const targetInstall = pluginInstalls.find(
        (install) => install.id === installId,
      );
      const targetPlugin = targetInstall
        ? plugins.find((plugin) => plugin.id === targetInstall.plugin_id)
        : null;
      const targetName =
        targetPlugin?.name ||
        t("cardNav.fallbackPreset", {
          id: targetInstall?.plugin_id ?? installId,
        });
      const previousInstalls = pluginInstalls;
      try {
        if (shouldEnable && otherEnabledInstalls.length > 0) {
          await pluginsService.bulkUpdateInstalls({
            enabled: false,
            install_ids: otherEnabledInstalls.map((install) => install.id),
          });
        }

        const updated = await pluginsService.updateInstall(installId, {
          enabled: shouldEnable,
        });

        setPluginInstalls((prev) =>
          prev.map((install) => {
            if (install.id === installId) {
              return updated;
            }
            if (
              shouldEnable &&
              otherEnabledInstalls.some((other) => other.id === install.id)
            ) {
              return { ...install, enabled: false };
            }
            return install;
          }),
        );
        invalidateStartupPreloadValues(["pluginInstalls"]);
        if (shouldEnable) {
          playInstallSound();
          const extraNote =
            otherEnabledInstalls.length > 0
              ? ` ${t("library.pluginsManager.toasts.exclusiveEnabled")}`
              : "";
          toast.success(
            `${targetName} ${t("library.pluginsManager.toasts.enabled")}${extraNote}`,
          );
        }
      } catch (error) {
        console.error("[CardNav] Failed to toggle Plugin:", error);
        if (shouldEnable && otherEnabledInstalls.length > 0) {
          try {
            await pluginsService.bulkUpdateInstalls({
              enabled: true,
              install_ids: otherEnabledInstalls.map((install) => install.id),
            });
          } catch (restoreError) {
            console.error(
              "[CardNav] Failed to restore preset toggles:",
              restoreError,
            );
          }
        }
        setPluginInstalls(previousInstalls);
      }
    },
    [pluginInstalls, plugins, t],
  );

  // Handle warning icon click
  const handleWarningClick = useCallback(
    (type: "mcp" | "skill", count: number) => {
      toast.warning(
        t(`hero.warnings.tooMany${type === "mcp" ? "Mcps" : "Skills"}`, {
          count,
        }),
      );
    },
    [t],
  );

  const handleOpenDialog = useCallback(
    (nextOpen: boolean) => {
      setIsDialogOpen(nextOpen);
      if (nextOpen) {
        void fetchData();
      }
    },
    [fetchData],
  );

  const handleEntryClick = useCallback(() => {
    handleOpenDialog(true);
  }, [handleOpenDialog]);

  const navigateToCapabilityView = useCallback(
    (viewId: CapabilityViewId) => {
      router.push(`/${lng}/capabilities?view=${viewId}&from=home`);
    },
    [lng, router],
  );

  const handleCardClick = useCallback(
    (viewId: CapabilityViewId) => {
      navigateToCapabilityView(viewId);
    },
    [navigateToCapabilityView],
  );

  const countEnabled = useCallback((items: InstalledItem[]) => {
    return items.reduce((count, item) => (item.enabled ? count + 1 : count), 0);
  }, []);

  const mcpEnabledCount = countEnabled(installedMcps);
  const skillEnabledCount = countEnabled(installedSkills);
  const pluginEnabledCount = countEnabled(installedPlugins);

  const previewItems = useMemo<PreviewItem[]>(() => {
    const enabledItems: PreviewItem[] = [
      ...installedMcps
        .filter((item) => item.enabled)
        .map((item) => ({
          id: `mcp-${item.id}`,
          name: item.name,
          type: "mcp" as const,
        })),
      ...installedSkills
        .filter((item) => item.enabled)
        .map((item) => ({
          id: `skill-${item.id}`,
          name: item.name,
          type: "skill" as const,
        })),
      ...installedPlugins
        .filter((item) => item.enabled)
        .map((item) => ({
          id: `plugin-${item.id}`,
          name: item.name,
          type: "plugin" as const,
        })),
    ];

    return enabledItems.slice(0, 6);
  }, [installedMcps, installedPlugins, installedSkills]);

  const hiddenPreviewCount = Math.max(
    mcpEnabledCount +
      skillEnabledCount +
      pluginEnabledCount -
      previewItems.length,
    0,
  );

  const renderItemBadges = (
    items: InstalledItem[],
    emptyText: string,
    type: "mcp" | "skill" | "plugin",
  ) => {
    if (isLoading && !hasFetched) {
      return (
        <div className="flex flex-col gap-1">
          <SkeletonText className="h-3 w-20" />
          <SkeletonText className="h-3 w-24" />
          <SkeletonText className="h-3 w-16" />
        </div>
      );
    }

    if (items.length === 0) {
      return (
        <span className="text-xs italic text-muted-foreground">
          {emptyText}
        </span>
      );
    }

    const toggleFn =
      type === "mcp"
        ? toggleMcpEnabled
        : type === "skill"
          ? toggleSkillEnabled
          : togglePluginEnabled;

    return (
      <div className="flex flex-col gap-2">
        {/* Item list */}
        <div className="flex flex-col gap-1 max-h-[180px] overflow-y-auto -mr-1 pr-2 [&::-webkit-scrollbar]:w-1 [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-muted-foreground/10 [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/30 transition-colors">
          <StaggeredEntrance show={hasFetched} staggerDelay={30} duration={300}>
            {items.map((item) => (
              <button
                key={item.id}
                className={cn(
                  "group/item flex items-center gap-2.5 px-2.5 py-1.5 text-xs font-medium rounded-md transition-all duration-200 text-left w-full cursor-pointer select-none",
                  "text-muted-foreground hover:text-foreground hover:bg-muted/60 active:bg-muted/80",
                )}
                onClick={(e) => {
                  e.stopPropagation();
                  toggleFn(item.installId, item.enabled);
                }}
                type="button"
              >
                <div
                  className={cn(
                    "w-2 h-2 rounded-full transition-all duration-300 flex-shrink-0",
                    item.enabled
                      ? "bg-primary shadow-[0_0_6px_-1px_hsl(var(--primary)/0.6)] scale-100"
                      : "bg-muted-foreground/30 scale-90 group-hover/item:bg-muted-foreground/50",
                  )}
                />
                <span className="flex-1 truncate tracking-tight opacity-90 group-hover/item:opacity-100">
                  {item.name}
                </span>
              </button>
            ))}
          </StaggeredEntrance>
        </div>
      </div>
    );
  };

  const handleDismiss = useCallback(() => {
    onDismiss?.();
  }, [onDismiss]);

  return (
    <div className={cn("w-full", className)}>
      <nav
        className={cn(
          "relative overflow-hidden transition-all duration-[0.4s] ease-[cubic-bezier(0.23,1,0.32,1)]",
          embedded
            ? "bg-transparent"
            : "rounded-xl border border-border bg-card/50 backdrop-blur-md hover:shadow-[0_12px_40px_-12px_rgba(var(--foreground),0.15)] hover:bg-card/80",
        )}
      >
        {/* Entry Bar */}
        <div
          role="button"
          tabIndex={0}
          aria-label={displayText}
          onClick={handleEntryClick}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              handleEntryClick();
            }
          }}
          className={cn(
            "group flex cursor-pointer items-center justify-between gap-3 rounded-xl transition-colors hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20",
            embedded ? "px-4 py-2.5" : "p-3.5",
          )}
        >
          <div className="flex min-w-0 items-center gap-2.5">
            <Plug
              className={cn(
                "size-4 flex-shrink-0 text-muted-foreground transition-all duration-300",
                isDialogOpen && "rotate-12",
              )}
            />
            <span className="truncate text-sm font-medium text-muted-foreground transition-colors duration-300">
              {displayText}
            </span>
          </div>

          <div className="flex items-center gap-1.5">
            {previewItems.map((item) => {
              const Icon =
                item.type === "mcp"
                  ? Server
                  : item.type === "skill"
                    ? Sparkles
                    : Plug;

              return (
                <span
                  key={item.id}
                  title={item.name}
                  className="inline-flex size-7 items-center justify-center rounded-full border border-border/60 bg-muted/40 text-muted-foreground"
                >
                  <Icon className="size-3.5" />
                </span>
              );
            })}

            {hiddenPreviewCount > 0 ? (
              <span className="inline-flex h-7 min-w-7 items-center justify-center rounded-full border border-border/60 bg-muted/40 px-2 text-xs text-muted-foreground">
                +{hiddenPreviewCount}
              </span>
            ) : null}

            {!isLoading &&
            previewItems.length === 0 &&
            hiddenPreviewCount === 0 ? (
              <span className="text-xs text-muted-foreground">
                {t("cardNav.comingSoon")}
              </span>
            ) : null}

            {showDismiss ? (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  handleDismiss();
                }}
                className="inline-flex size-7 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
                aria-label={t("common.close")}
              >
                <X className="size-4" />
              </button>
            ) : null}
          </div>
        </div>
      </nav>

      <Dialog open={isDialogOpen} onOpenChange={handleOpenDialog}>
        <DialogContent className="max-w-8xl border-border bg-background p-0 text-foreground">
          <DialogHeader className="border-b border-border px-6 py-4">
            <DialogTitle>{displayText}</DialogTitle>
          </DialogHeader>
          <div className="p-4 md:p-6">
            <div className="flex flex-nowrap gap-4 overflow-x-auto [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:grid md:grid-cols-3 md:overflow-visible">
              {/* MCP Card */}
              <div className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 px-4 py-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink">
                <div className="mb-3 flex min-w-0 items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => handleCardClick("mcp")}
                    className="flex h-10 min-w-0 items-center gap-2.5 rounded-2xl border border-border/50 bg-muted/60 px-3 text-foreground transition-all duration-200 hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
                    aria-label={t("cardNav.mcp")}
                  >
                    <Server className="size-4 text-muted-foreground" />
                    <span className="text-base font-semibold tracking-[-0.01em]">
                      {t("cardNav.mcp")}
                    </span>
                  </button>
                  {mcpEnabledCount > MCP_LIMIT ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleWarningClick("mcp", mcpEnabledCount);
                      }}
                      className="flex items-center justify-center size-6 rounded-full hover:bg-amber-500/20 transition-colors"
                      type="button"
                      title={t("cardNav.clickForDetails")}
                    >
                      <AlertTriangle className="size-4 text-amber-500" />
                    </button>
                  ) : null}
                </div>
                {renderItemBadges(
                  installedMcps,
                  t("cardNav.noMcpInstalled"),
                  "mcp",
                )}
              </div>

              {/* Skill Card */}
              <div className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 px-4 py-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink">
                <div className="mb-3 flex min-w-0 items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => handleCardClick("skills")}
                    className="flex h-10 min-w-0 items-center gap-2.5 rounded-2xl border border-border/50 bg-muted/60 px-3 text-foreground transition-all duration-200 hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
                    aria-label={t("cardNav.skills")}
                  >
                    <Sparkles className="size-4 text-muted-foreground" />
                    <span className="text-base font-semibold tracking-[-0.01em]">
                      {t("cardNav.skills")}
                    </span>
                  </button>
                  {skillEnabledCount > SKILL_LIMIT ? (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleWarningClick("skill", skillEnabledCount);
                      }}
                      className="flex items-center justify-center size-6 rounded-full hover:bg-amber-500/20 transition-colors"
                      type="button"
                      title={t("cardNav.clickForDetails")}
                    >
                      <AlertTriangle className="size-4 text-amber-500" />
                    </button>
                  ) : null}
                </div>
                {renderItemBadges(
                  installedSkills,
                  t("cardNav.noSkillsInstalled"),
                  "skill",
                )}
              </div>

              {/* Presets Card */}
              <div className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 px-4 py-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink">
                <div className="mb-3 flex min-w-0 items-center justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => handleCardClick("presets")}
                    className="flex h-10 min-w-0 items-center gap-2.5 rounded-2xl border border-border/50 bg-muted/60 px-3 text-foreground transition-all duration-200 hover:bg-muted/70 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
                    aria-label={t("cardNav.plugins")}
                  >
                    <Plug className="size-4 text-muted-foreground" />
                    <span className="text-base font-semibold tracking-[-0.01em]">
                      {t("cardNav.plugins")}
                    </span>
                  </button>
                </div>
                {renderItemBadges(
                  installedPlugins,
                  t("cardNav.noPluginsInstalled"),
                  "plugin",
                )}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default CardNav;
