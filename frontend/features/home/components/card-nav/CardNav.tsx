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
import {
  Plug,
  Server,
  Sparkles,
  AppWindow,
  Loader2,
  ChevronRight,
} from "lucide-react";
import { mcpService } from "@/features/mcp/services/mcp-service";
import { skillsService } from "@/features/skills/services/skills-service";
import type { McpServer, UserMcpInstall } from "@/features/mcp/types";
import type { Skill, UserSkillInstall } from "@/features/skills/types";
import { useAppShell } from "@/components/shared/app-shell-context";
import { cn } from "@/lib/utils";

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
  triggerText = "将您的工具连接到 Poco",
  className = "",
  forceExpanded = false,
}: CardNavProps) {
  const router = useRouter();
  const { lng } = useAppShell();
  const [isExpanded, setIsExpanded] = useState(false);
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
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(false);

  // Fetch MCP and Skill data
  const fetchData = useCallback(async () => {
    if (hasFetched || isLoading) return;

    setIsLoading(true);
    try {
      const [mcpServersData, mcpInstallsData, skillsData, skillInstallsData] =
        await Promise.all([
          mcpService.listServers(),
          mcpService.listInstalls(),
          skillsService.listSkills(),
          skillsService.listInstalls(),
        ]);
      setMcpServers(mcpServersData);
      setMcpInstalls(mcpInstallsData);
      setSkills(skillsData);
      setSkillInstalls(skillInstallsData);
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
      name: server?.name || `MCP #${install.server_id}`,
      enabled: install.enabled,
      installId: install.id,
    };
  });

  // Get all installed Skills
  const installedSkills: InstalledItem[] = skillInstalls.map((install) => {
    const skill = skills.find((s) => s.id === install.skill_id);
    return {
      id: install.skill_id,
      name: skill?.name || `Skill #${install.skill_id}`,
      enabled: install.enabled,
      installId: install.id,
    };
  });

  // Toggle MCP enabled state
  const toggleMcpEnabled = useCallback(
    async (installId: number, currentEnabled: boolean) => {
      try {
        await mcpService.updateInstall(installId, { enabled: !currentEnabled });
        setMcpInstalls((prev) =>
          prev.map((install) =>
            install.id === installId
              ? { ...install, enabled: !currentEnabled }
              : install,
          ),
        );
      } catch (error) {
        console.error("[CardNav] Failed to toggle MCP:", error);
      }
    },
    [],
  );

  // Toggle Skill enabled state
  const toggleSkillEnabled = useCallback(
    async (installId: number, currentEnabled: boolean) => {
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
      } catch (error) {
        console.error("[CardNav] Failed to toggle Skill:", error);
      }
    },
    [],
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

  const handleLabelClick = useCallback(
    (e: React.MouseEvent, path: string) => {
      e.stopPropagation();
      router.push(`/${lng}/${path}?from=home`);
    },
    [router, lng],
  );

  const renderItemBadges = (
    items: InstalledItem[],
    emptyText: string,
    type: "mcp" | "skill",
  ) => {
    if (isLoading) {
      return (
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Loader2 className="size-3 animate-spin" />
          <span>同步中...</span>
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

    const toggleFn = type === "mcp" ? toggleMcpEnabled : toggleSkillEnabled;

    return (
      <div className="flex flex-col gap-1.5 max-h-[180px] overflow-y-auto pr-2 scrollbar-thin scrollbar-thumb-muted-foreground/40 scrollbar-track-muted/30 hover:scrollbar-thumb-muted-foreground/60">
        {items.map((item) => (
          <button
            key={item.id}
            className={cn(
              "flex items-center gap-2 p-2 text-xs font-medium rounded-md border transition-all text-left w-full cursor-pointer",
              "bg-muted/40 text-muted-foreground border-border/40 hover:bg-muted/60 hover:border-border/60",
            )}
            onClick={(e) => {
              e.stopPropagation();
              toggleFn(item.installId, item.enabled);
            }}
            type="button"
          >
            <span
              className={cn(
                "w-2.5 h-2.5 rounded-full flex-shrink-0 transition-all",
                item.enabled
                  ? "bg-primary shadow-sm"
                  : "bg-zinc-400 dark:bg-zinc-500",
              )}
            />
            <span className="flex-1 truncate">{item.name}</span>
          </button>
        ))}
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
            {triggerText}
          </span>
        </div>

        {/* Modular Content */}
        <div ref={contentRef} className="overflow-hidden">
          <div className="grid grid-cols-3 gap-4 p-4 border-t border-border/50 max-[900px]:grid-cols-1">
            {/* MCP Card */}
            <div
              ref={setCardRef(0)}
              className="group relative flex flex-col p-5 rounded-lg border bg-muted/30 border-border/50 hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] min-h-[140px]"
            >
              <div className="flex items-center gap-2.5 mb-3">
                <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                  <Server className="size-[1.125rem]" />
                </div>
                <button
                  className="flex items-center gap-1 bg-transparent border-none cursor-pointer transition-all duration-200 rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                  onClick={(e) => handleLabelClick(e, "capabilities/mcp")}
                  type="button"
                >
                  <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                    MCP
                  </span>
                  <ChevronRight className="size-3.5 text-muted-foreground transition-transform duration-200 hover:translate-x-0.5" />
                </button>
              </div>
              {renderItemBadges(installedMcps, "未安装 MCP", "mcp")}
            </div>

            {/* Skill Card */}
            <div
              ref={setCardRef(1)}
              className="group relative flex flex-col p-5 rounded-lg border bg-muted/30 border-border/50 hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] min-h-[140px]"
            >
              <div className="flex items-center gap-2.5 mb-3">
                <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                  <Sparkles className="size-[1.125rem]" />
                </div>
                <button
                  className="flex items-center gap-1 bg-transparent border-none cursor-pointer transition-all duration-200 rounded px-2 py-1 -mx-2 -my-1 hover:bg-muted/50 focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-2"
                  onClick={(e) => handleLabelClick(e, "capabilities/skills")}
                  type="button"
                >
                  <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                    Skill
                  </span>
                  <ChevronRight className="size-3.5 text-muted-foreground transition-transform duration-200 hover:translate-x-0.5" />
                </button>
              </div>
              {renderItemBadges(installedSkills, "未安装技能", "skill")}
            </div>

            {/* App Card */}
            <div className="group relative flex flex-col p-5 rounded-lg border bg-muted/30 border-border/50 hover:-translate-y-0.5 hover:bg-muted/40 hover:shadow-[0_4px_12px_-2px_rgba(var(--foreground),0.05)] transition-all duration-300 ease-[cubic-bezier(0.23,1,0.32,1)] min-h-[140px]">
              <div className="flex items-center gap-2.5 mb-3">
                <div className="flex items-center justify-center size-9 rounded-md bg-muted text-muted-foreground transition-all duration-300">
                  <AppWindow className="size-[1.125rem]" />
                </div>
                <span className="text-base font-semibold tracking-[-0.01em] text-foreground">
                  应用
                </span>
              </div>
              <span className="text-xs italic text-muted-foreground">
                即将推出
              </span>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}

export default CardNav;
