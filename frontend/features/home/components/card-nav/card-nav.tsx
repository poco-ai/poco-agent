"use client";

import {
  useLayoutEffect,
  useRef,
  useState,
  useCallback,
  useEffect,
} from "react";
import { useRouter } from "next/navigation";
import { gsap } from "gsap";
import { Plug, Server, Sparkles, ChevronRight, Power } from "lucide-react";
import { mcpService } from "@/features/capabilities/mcp/services/mcp-service";
import { skillsService } from "@/features/capabilities/skills/services/skills-service";
import { pluginsService } from "@/features/capabilities/plugins/services/plugins-service";
import type {
  McpServer,
  UserMcpInstall,
} from "@/features/capabilities/mcp/types";
import { Skill, UserSkillInstall } from "@/features/capabilities/skills/types";
import type {
  Plugin,
  UserPluginInstall,
} from "@/features/capabilities/plugins/types";
import { useAppShell } from "@/components/shared/app-shell-context";
import { cn } from "@/lib/utils";
import { playMcpInstallSound } from "@/lib/utils/sound";
import { useT } from "@/lib/i18n/client";
import { setPendingCapabilityView } from "@/features/capabilities/lib/capability-view-state";
import { toast } from "sonner";
import { AlertTriangle } from "lucide-react";
import { SkeletonText } from "@/components/ui/skeleton-shimmer";
import { StaggeredEntrance } from "@/components/ui/staggered-entrance";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const MCP_LIMIT = 3;
const SKILL_LIMIT = 5;

type CapabilityViewId = "mcp" | "skills" | "presets";

export interface CardNavProps {
  triggerText?: string;
  className?: string;
  forceExpanded?: boolean;
}

interface InstalledItem {
  id: number;
  name: string;
  enabled: boolean;
  installId: number;
}

/**
 * CardNav Component
 *
 * An expandable card that shows MCP, Skill, and App sections on hover
 */
export function CardNav({
  triggerText,
  className = "",
  forceExpanded = false,
}: CardNavProps) {
  const router = useRouter();
  const { lng } = useAppShell();
  const { t } = useT("translation");
  const [isExpanded, setIsExpanded] = useState(false);

  // Default trigger text from i18n if not provided
  const displayText = triggerText ?? t("hero.tools");
  const navRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const cardsRef = useRef<(HTMLDivElement | null)[]>([]);
  const tlRef = useRef<gsap.core.Timeline | null>(null);
  const isHoveringRef = useRef(false);
  const closeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // API data state
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [mcpInstalls, setMcpInstalls] = useState<UserMcpInstall[]>([]);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [skillInstalls, setSkillInstalls] = useState<UserSkillInstall[]>([]);
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [pluginInstalls, setPluginInstalls] = useState<UserPluginInstall[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  // Fetch MCP/Skill/Plugin data
  const fetchData = useCallback(async () => {
    if (hasFetched || isLoading) return;

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
    } catch (error) {
      console.error("[CardNav] Failed to fetch data:", error);
    } finally {
      setIsLoading(false);
    }
  }, [hasFetched, isLoading]);

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
        if (!currentEnabled) {
          playMcpInstallSound();
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
        if (!currentEnabled) {
          playMcpInstallSound();
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
      try {
        await pluginsService.updateInstall(installId, {
          enabled: !currentEnabled,
        });
        setPluginInstalls((prev) =>
          prev.map((install) =>
            install.id === installId
              ? { ...install, enabled: !currentEnabled }
              : install,
          ),
        );
        if (!currentEnabled) {
          playMcpInstallSound();
        }
      } catch (error) {
        console.error("[CardNav] Failed to toggle Plugin:", error);
      }
    },
    [],
  );

  // Batch toggle all MCPs
  const batchToggleMcps = useCallback(
    async (enable: boolean) => {
      try {
        const installIds = mcpInstalls
          .filter((install) => install.enabled !== enable)
          .map((install) => install.id);
        if (installIds.length > 0) {
          await mcpService.bulkUpdateInstalls({
            enabled: enable,
            install_ids: installIds,
          });
        }
        setMcpInstalls((prev) =>
          prev.map((install) => ({ ...install, enabled: enable })),
        );
        if (enable) {
          const count = mcpInstalls.length;
          if (count > MCP_LIMIT) {
            toast.warning(t("hero.warnings.tooManyMcps", { count }));
          } else {
            playMcpInstallSound();
          }
        }
      } catch (error) {
        console.error("[CardNav] Failed to batch toggle MCPs:", error);
        toast.error(t("hero.toasts.actionFailed"));
      }
    },
    [mcpInstalls, t],
  );

  // Batch toggle all Skills
  const batchToggleSkills = useCallback(
    async (enable: boolean) => {
      try {
        const installIds = skillInstalls
          .filter((install) => install.enabled !== enable)
          .map((install) => install.id);
        if (installIds.length > 0) {
          await skillsService.bulkUpdateInstalls({
            enabled: enable,
            install_ids: installIds,
          });
        }
        setSkillInstalls((prev) =>
          prev.map((install) => ({ ...install, enabled: enable })),
        );
        if (enable) {
          const count = skillInstalls.length;
          if (count > SKILL_LIMIT) {
            toast.warning(t("hero.warnings.tooManySkills", { count }));
          } else {
            playMcpInstallSound();
          }
        }
      } catch (error) {
        console.error("[CardNav] Failed to batch toggle Skills:", error);
        toast.error(t("hero.toasts.actionFailed"));
      }
    },
    [skillInstalls, t],
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

  const createTimeline = useCallback(() => {
    const navEl = navRef.current;
    const cards = cardsRef.current.filter(Boolean);
    if (!navEl) return null;

    gsap.set(navEl, { height: 48 });
    gsap.set(cards, { opacity: 0, scale: 0.95, y: 15 });

    const tl = gsap.timeline({
      paused: true,
      defaults: { ease: "power2.out" },
    });

    tl.to(navEl, { height: "auto", duration: 0.15 });
    tl.to(
      cards,
      { opacity: 1, scale: 1, y: 0, duration: 0.25, stagger: 0.08 },
      "-=0.25",
    );

    return tl;
  }, []);

  useLayoutEffect(() => {
    const tl = createTimeline();
    tlRef.current = tl;
    return () => {
      tl?.kill();
      tlRef.current = null;
    };
  }, [createTimeline]);

  const openMenu = useCallback(() => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }

    if (!isExpanded) {
      setIsExpanded(true);
      fetchData();

      requestAnimationFrame(() => {
        if (!tlRef.current) {
          tlRef.current = createTimeline();
        }
        tlRef.current?.play(0);
      });
    }
  }, [isExpanded, fetchData, createTimeline]);

  const closeMenu = useCallback(() => {
    const tl = tlRef.current;
    if (!tl || !isExpanded) return;

    tl.reverse();
    tl.eventCallback("onReverseComplete", () => {
      setIsExpanded(false);
    });
  }, [isExpanded]);

  // Handle forceExpanded prop
  useEffect(() => {
    if (forceExpanded) {
      openMenu();
    } else if (!isHoveringRef.current) {
      closeMenu();
    }
  }, [forceExpanded, openMenu, closeMenu]);

  const handleMouseEnter = useCallback(() => {
    isHoveringRef.current = true;
    openMenu();
  }, [openMenu]);

  const handleMouseLeave = useCallback(() => {
    isHoveringRef.current = false;
    closeTimeoutRef.current = setTimeout(() => {
      if (!isHoveringRef.current && !forceExpanded) {
        closeMenu();
      }
    }, 50);
  }, [closeMenu, forceExpanded]);

  const setCardRef = (index: number) => (el: HTMLDivElement | null) => {
    cardsRef.current[index] = el;
  };

  const navigateToCapabilityView = useCallback(
    (viewId: CapabilityViewId) => {
      setPendingCapabilityView(viewId);
      router.push(`/${lng}/capabilities?view=${viewId}`);
    },
    [lng, router],
  );

  const handleLabelClick = useCallback(
    (e: React.MouseEvent, viewId: CapabilityViewId) => {
      e.stopPropagation();
      navigateToCapabilityView(viewId);
    },
    [navigateToCapabilityView],
  );

  const handleCardClick = useCallback(
    (viewId: CapabilityViewId) => {
      navigateToCapabilityView(viewId);
    },
    [navigateToCapabilityView],
  );

  const handleCardKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>, viewId: CapabilityViewId) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        navigateToCapabilityView(viewId);
      }
    },
    [navigateToCapabilityView],
  );

  const countEnabled = useCallback((items: InstalledItem[]) => {
    return items.reduce((count, item) => (item.enabled ? count + 1 : count), 0);
  }, []);

  const mcpEnabledCount = countEnabled(installedMcps);
  const skillEnabledCount = countEnabled(installedSkills);

  const getToggleTooltip = (
    type: "mcp" | "skill" | "plugin",
    hasItems: boolean,
    isActive: boolean,
  ) => {
    if (!hasItems) {
      return t(
        `cardNav.${
          type === "mcp"
            ? "noMcpInstalled"
            : type === "skill"
              ? "noSkillsInstalled"
              : "noPluginsInstalled"
        }`,
      );
    }

    return t(`cardNav.${isActive ? "turnOffAll" : "turnOnAll"}`);
  };

  const renderAggregateToggle = (
    type: "mcp" | "skill" | "plugin",
    hasItems: boolean,
    enabledCount: number,
    toggleFn: (enable: boolean) => Promise<void> | void,
  ) => {
    const isActive = enabledCount > 0;
    const tooltipLabel = getToggleTooltip(type, hasItems, isActive);
    const isHighlighted = isActive;
    return (
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            aria-pressed={isHighlighted}
            aria-label={tooltipLabel}
            disabled={!hasItems}
            onClick={async (event) => {
              event.stopPropagation();
              if (!hasItems) return;
              const nextEnable = isActive ? false : true;
              await toggleFn(nextEnable);
            }}
            className={cn(
              "relative flex size-7 items-center justify-center rounded-full border transition-all duration-200",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40",
              !hasItems
                ? "cursor-not-allowed border-border/40 bg-transparent text-muted-foreground/40"
                : isHighlighted
                  ? "border-primary/40 bg-primary/10 text-primary shadow-[0_6px_20px_-10px_hsl(var(--primary)/0.7)]"
                  : "border-border/60 text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )}
          >
            <Power className="size-3.5" />
          </button>
        </TooltipTrigger>
        <TooltipContent side="top" sideOffset={4}>
          <span>{tooltipLabel}</span>
        </TooltipContent>
      </Tooltip>
    );
  };

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

  return (
    <div className={cn("w-full", className)}>
      <nav
        ref={navRef}
        className={cn(
          "relative rounded-xl border border-border bg-card/50 overflow-hidden transition-all duration-[0.4s] ease-[cubic-bezier(0.23,1,0.32,1)] backdrop-blur-md",
          "hover:shadow-[0_12px_40px_-12px_rgba(var(--foreground),0.15)] hover:bg-card/80",
          isExpanded &&
            "shadow-[0_12px_40px_-12px_rgba(var(--foreground),0.15)] bg-card/80",
        )}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        {/* Entry Bar */}
        <div className="group flex items-center gap-3 p-3.5 cursor-pointer">
          <Plug
            className={cn(
              "size-5 flex-shrink-0 text-muted-foreground transition-all duration-300",
              isExpanded && "rotate-12",
            )}
          />
          <span className="text-sm font-medium text-muted-foreground transition-colors duration-300">
            {displayText}
          </span>
        </div>

        {/* Modular Content */}
        <div ref={contentRef} className="overflow-hidden">
          <div className="flex flex-nowrap gap-4 overflow-x-auto border-t border-border/50 p-4 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden md:grid md:grid-cols-3 md:overflow-visible">
            {/* MCP Card */}
            <div
              ref={setCardRef(0)}
              role="button"
              tabIndex={0}
              aria-label={t("cardNav.mcp")}
              onClick={() => handleCardClick("mcp")}
              onKeyDown={(event) => handleCardKeyDown(event, "mcp")}
              className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 p-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="mb-3 flex min-w-0 items-center justify-between gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <div className="flex shrink-0 items-center gap-2.5">
                  <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                    <Server className="size-[1.125rem]" />
                  </div>
                  <button
                    className="flex items-center gap-1 bg-transparent border-none cursor-pointer transition-all duration-200 rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                    onClick={(e) => handleLabelClick(e, "mcp")}
                    type="button"
                  >
                    <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                      {t("cardNav.mcp")}
                    </span>
                    <ChevronRight className="size-3.5 text-muted-foreground transition-transform duration-200 hover:translate-x-0.5" />
                  </button>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {renderAggregateToggle(
                    "mcp",
                    installedMcps.length > 0,
                    mcpEnabledCount,
                    batchToggleMcps,
                  )}
                  {mcpEnabledCount > MCP_LIMIT && (
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
                  )}
                </div>
              </div>
              {renderItemBadges(
                installedMcps,
                t("cardNav.noMcpInstalled"),
                "mcp",
              )}
            </div>

            {/* Skill Card */}
            <div
              ref={setCardRef(1)}
              role="button"
              tabIndex={0}
              aria-label={t("cardNav.skills")}
              onClick={() => handleCardClick("skills")}
              onKeyDown={(event) => handleCardKeyDown(event, "skills")}
              className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 p-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="mb-3 flex min-w-0 items-center justify-between gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <div className="flex shrink-0 items-center gap-2.5">
                  <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                    <Sparkles className="size-[1.125rem]" />
                  </div>
                  <button
                    className="flex items-center gap-1 bg-transparent border-none cursor-pointer transition-all duration-200 rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                    onClick={(e) => handleLabelClick(e, "skills")}
                    type="button"
                  >
                    <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                      {t("cardNav.skills")}
                    </span>
                    <ChevronRight className="size-3.5 text-muted-foreground transition-transform duration-200 hover:translate-x-0.5" />
                  </button>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {renderAggregateToggle(
                    "skill",
                    installedSkills.length > 0,
                    skillEnabledCount,
                    batchToggleSkills,
                  )}
                  {skillEnabledCount > SKILL_LIMIT && (
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
                  )}
                </div>
              </div>
              {renderItemBadges(
                installedSkills,
                t("cardNav.noSkillsInstalled"),
                "skill",
              )}
            </div>

            {/* Presets Card */}
            <div
              ref={setCardRef(2)}
              role="button"
              tabIndex={0}
              aria-label={t("cardNav.plugins")}
              onClick={() => handleCardClick("presets")}
              onKeyDown={(event) => handleCardKeyDown(event, "presets")}
              className="group relative flex min-w-[260px] shrink-0 flex-col rounded-lg border border-border/50 bg-muted/30 p-5 transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] min-h-[140px] md:min-w-0 md:shrink cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="mb-3 flex min-w-0 items-center gap-3 overflow-x-auto whitespace-nowrap [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                <div className="flex shrink-0 items-center gap-2.5">
                  <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                    <Plug className="size-[1.125rem]" />
                  </div>
                  <button
                    className="flex items-center gap-1 bg-transparent border-none cursor-pointer transition-all duration-200 rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                    onClick={(e) => handleLabelClick(e, "presets")}
                    type="button"
                  >
                    <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                      {t("cardNav.plugins")}
                    </span>
                    <ChevronRight className="size-3.5 text-muted-foreground transition-transform duration-200 hover:translate-x-0.5" />
                  </button>
                </div>
              </div>
              {renderItemBadges(
                installedPlugins,
                t("cardNav.noPluginsInstalled"),
                "plugin",
              )}
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}

export default CardNav;
