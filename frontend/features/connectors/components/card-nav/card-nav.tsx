"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { Plug, Server, Sparkles, X } from "lucide-react";
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
} from "@/lib/startup-preload";
import { toast } from "sonner";
import { useCapabilityToggle } from "@/features/connectors";
import {
  ConnectToolsDialog,
  type CapabilityCardConfig,
} from "./connect-tools-dialog";

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
  const capabilityToggle = useCapabilityToggle();
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

  // Get all installed MCPs (merge with context overrides)
  const installedMcps: InstalledItem[] = useMemo(() => {
    return mcpInstalls.map((install) => {
      const server = mcpServers.find((s) => s.id === install.server_id);
      const contextEnabled = capabilityToggle?.getMcpEnabled(
        install.server_id,
        install.enabled,
      );
      return {
        id: install.server_id,
        name:
          server?.name || t("cardNav.fallbackMcp", { id: install.server_id }),
        enabled: contextEnabled ?? install.enabled,
        installId: install.id,
      };
    });
  }, [mcpInstalls, mcpServers, capabilityToggle, t]);

  // Get all installed Skills (merge with context overrides)
  const installedSkills: InstalledItem[] = useMemo(() => {
    return skillInstalls.map((install) => {
      const skill = skills.find((s) => s.id === install.skill_id);
      const contextEnabled = capabilityToggle?.getSkillEnabled(
        install.skill_id,
        install.enabled,
      );
      return {
        id: install.skill_id,
        name:
          skill?.name || t("cardNav.fallbackSkill", { id: install.skill_id }),
        enabled: contextEnabled ?? install.enabled,
        installId: install.id,
      };
    });
  }, [skillInstalls, skills, capabilityToggle, t]);

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

  // Toggle MCP enabled state (local only, no API call)
  const toggleMcpEnabled = useCallback(
    (installId: number, currentEnabled: boolean) => {
      const targetInstall = mcpInstalls.find(
        (install) => install.id === installId,
      );
      if (!targetInstall) return;

      const newEnabled = !currentEnabled;

      // Check if enabling would exceed the limit
      const currentEnabledCount = installedMcps.filter((i) => i.enabled).length;
      if (newEnabled && currentEnabledCount >= MCP_LIMIT) {
        toast.warning(t("hero.warnings.mcpLimitReached"));
        return;
      }

      setMcpInstalls((prev) =>
        prev.map((install) =>
          install.id === installId
            ? { ...install, enabled: newEnabled }
            : install,
        ),
      );

      // Sync with context
      capabilityToggle?.toggleMcp(targetInstall.server_id, newEnabled);

      if (newEnabled) {
        playInstallSound();
      }

      // Check if we've exceeded the limit after enabling
      const newEnabledCount = newEnabled
        ? currentEnabledCount + 1
        : currentEnabledCount;
      if (newEnabledCount > MCP_LIMIT) {
        toast.warning(
          t("hero.warnings.tooManyMcps", { count: newEnabledCount }),
        );
      }
    },
    [mcpInstalls, installedMcps, capabilityToggle, t],
  );

  // Toggle Skill enabled state (local only, no API call)
  const toggleSkillEnabled = useCallback(
    (installId: number, currentEnabled: boolean) => {
      const targetInstall = skillInstalls.find(
        (install) => install.id === installId,
      );
      if (!targetInstall) return;

      const newEnabled = !currentEnabled;

      // Check if enabling would exceed the limit
      const currentEnabledCount = installedSkills.filter(
        (i) => i.enabled,
      ).length;
      if (newEnabled && currentEnabledCount >= SKILL_LIMIT) {
        toast.warning(t("hero.warnings.skillLimitReached"));
        return;
      }

      setSkillInstalls((prev) =>
        prev.map((install) =>
          install.id === installId
            ? { ...install, enabled: newEnabled }
            : install,
        ),
      );

      // Sync with context
      capabilityToggle?.toggleSkill(targetInstall.skill_id, newEnabled);

      if (newEnabled) {
        playInstallSound();
      }

      // Check if we've exceeded the limit after enabling
      const newEnabledCount = newEnabled
        ? currentEnabledCount + 1
        : currentEnabledCount;
      if (newEnabledCount > SKILL_LIMIT) {
        toast.warning(
          t("hero.warnings.tooManySkills", { count: newEnabledCount }),
        );
      }
    },
    [skillInstalls, installedSkills, capabilityToggle, t],
  );

  // Toggle Plugin enabled state (local only, no API call)
  const togglePluginEnabled = useCallback(
    (installId: number, currentEnabled: boolean) => {
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

      setPluginInstalls((prev) =>
        prev.map((install) => {
          if (install.id === installId) {
            return { ...install, enabled: shouldEnable };
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

  const handleDismiss = useCallback(() => {
    onDismiss?.();
  }, [onDismiss]);

  const canDismiss = showDismiss && typeof onDismiss === "function";
  const dialogCards: CapabilityCardConfig[] = useMemo(
    () => [
      {
        icon: Server,
        title: t("cardNav.mcp"),
        items: installedMcps,
        emptyText: t("cardNav.noMcpInstalled"),
        onToggle: toggleMcpEnabled,
        onNavigate: () => handleCardClick("mcp"),
        showWarning: mcpEnabledCount > MCP_LIMIT,
        onWarningClick: () => handleWarningClick("mcp", mcpEnabledCount),
      },
      {
        icon: Sparkles,
        title: t("cardNav.skills"),
        items: installedSkills,
        emptyText: t("cardNav.noSkillsInstalled"),
        onToggle: toggleSkillEnabled,
        onNavigate: () => handleCardClick("skills"),
        showWarning: skillEnabledCount > SKILL_LIMIT,
        onWarningClick: () => handleWarningClick("skill", skillEnabledCount),
      },
      {
        icon: Plug,
        title: t("cardNav.plugins"),
        items: installedPlugins,
        emptyText: t("cardNav.noPluginsInstalled"),
        onToggle: togglePluginEnabled,
        onNavigate: () => handleCardClick("presets"),
      },
    ],
    [
      t,
      installedMcps,
      installedSkills,
      installedPlugins,
      toggleMcpEnabled,
      toggleSkillEnabled,
      togglePluginEnabled,
      handleCardClick,
      handleWarningClick,
      mcpEnabledCount,
      skillEnabledCount,
    ],
  );

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
            embedded ? "min-h-12 px-4 py-2.5" : "min-h-14 p-3.5",
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

            {canDismiss ? (
              <button
                type="button"
                aria-label={t("common.close")}
                className="inline-flex size-7 items-center justify-center rounded-full border border-border/60 bg-muted/40 text-muted-foreground transition-colors hover:bg-muted/70 hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-foreground/20"
                onClick={(event) => {
                  event.stopPropagation();
                  handleDismiss();
                }}
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
        </div>
      </nav>

      <ConnectToolsDialog
        open={isDialogOpen}
        onOpenChange={handleOpenDialog}
        title={displayText}
        cards={dialogCards}
        isLoading={isLoading}
        hasFetched={hasFetched}
      />
    </div>
  );
}

export default CardNav;
