"use client";

import * as React from "react";
import { Badge } from "@/components/ui/badge";
import {
  Zap,
  Server,
  AppWindow,
  Plug,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { mcpService } from "@/features/capabilities/mcp/services/mcp-service";
import { skillsService } from "@/features/capabilities/skills/services/skills-service";
import { pluginsService } from "@/features/capabilities/plugins/services/plugins-service";
import type { McpServer } from "@/features/capabilities/mcp/types";
import type { Skill } from "@/features/capabilities/skills/types";
import type { Plugin } from "@/features/capabilities/plugins/types";
import type {
  SkillUse,
  McpStatusItem,
  ConfigSnapshot,
  BrowserState,
} from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";

interface StatusBarProps {
  // Runtime execution data (deprecated, now using configSnapshot)
  skills?: SkillUse[];
  mcpStatuses?: McpStatusItem[];
  browser?: BrowserState | null;
  // Configuration snapshot from session creation
  configSnapshot?: ConfigSnapshot | null;
  className?: string;
}

export function StatusBar({
  skills = [],
  mcpStatuses = [],
  browser = null,
  configSnapshot,
  className,
}: StatusBarProps) {
  const { t } = useT("translation");
  const [mcpServers, setMcpServers] = React.useState<McpServer[]>([]);
  const [allSkills, setAllSkills] = React.useState<Skill[]>([]);
  const [allPresets, setAllPresets] = React.useState<Plugin[]>([]);
  const isMobile = useIsMobile();

  const renderInteractiveCard = React.useCallback(
    (card: React.ReactNode, content: React.ReactNode) => {
      if (isMobile) {
        return (
          <Popover>
            <PopoverTrigger asChild>{card}</PopoverTrigger>
            <PopoverContent
              side="top"
              align="start"
              sideOffset={8}
              className="w-64 p-2 bg-card border-border shadow-lg"
            >
              {content}
            </PopoverContent>
          </Popover>
        );
      }

      return (
        <Tooltip>
          <TooltipTrigger asChild>{card}</TooltipTrigger>
          <TooltipContent
            side="top"
            className="p-2 bg-card border-border shadow-lg"
            sideOffset={8}
          >
            {content}
          </TooltipContent>
        </Tooltip>
      );
    },
    [isMobile],
  );

  // Load MCP servers and skills on mount
  React.useEffect(() => {
    const loadData = async () => {
      try {
        const [serversData, skillsData, pluginsData] = await Promise.all([
          mcpService.listServers(),
          skillsService.listSkills(),
          pluginsService.listPlugins(),
        ]);
        setMcpServers(serversData);
        setAllSkills(skillsData);
        setAllPresets(pluginsData);
      } catch (error) {
        console.error("[StatusBar] Failed to load config data:", error);
      }
    };

    loadData();
  }, []);

  // Find MCP servers by IDs from config snapshot
  const configuredMcpServers = React.useMemo(() => {
    const mcpServerIds = configSnapshot?.mcp_server_ids ?? [];
    return mcpServerIds
      .map((id) => mcpServers.find((server) => server.id === id))
      .filter((server): server is McpServer => server !== undefined);
  }, [configSnapshot?.mcp_server_ids, mcpServers]);

  // Find skills by IDs from config snapshot
  const configuredSkills = React.useMemo(() => {
    const skillIds = configSnapshot?.skill_ids ?? [];
    return skillIds
      .map((id) => allSkills.find((skill) => skill.id === id))
      .filter((skill): skill is Skill => skill !== undefined);
  }, [configSnapshot?.skill_ids, allSkills]);

  // Find presets by IDs from config snapshot
  const configuredPresets = React.useMemo(() => {
    const pluginIds = configSnapshot?.plugin_ids ?? [];
    return pluginIds
      .map((id) => allPresets.find((plugin) => plugin.id === id))
      .filter((plugin): plugin is Plugin => plugin !== undefined);
  }, [configSnapshot?.plugin_ids, allPresets]);

  const visibleMcpStatuses = React.useMemo(() => {
    // Hide built-in/internal MCP servers (e.g. executor-injected Playwright MCP).
    return (mcpStatuses ?? []).filter((mcp) => {
      const name = (mcp?.server_name || "").trim();
      return !name.startsWith("__poco_");
    });
  }, [mcpStatuses]);

  // Prefer config snapshot data, fallback to runtime data
  const hasSkills = configuredSkills.length > 0 || skills.length > 0;
  const hasMcp =
    configuredMcpServers.length > 0 || visibleMcpStatuses.length > 0;
  const hasPresets = configuredPresets.length > 0;
  const hasBrowser = Boolean(
    configSnapshot?.browser_enabled || browser?.enabled,
  );

  if (!hasSkills && !hasMcp && !hasPresets && !hasBrowser) {
    return null;
  }

  // Display skills from config snapshot (preferred) or runtime data
  const displaySkills =
    configuredSkills.length > 0
      ? configuredSkills.map((skill) => ({
          id: String(skill.id),
          name: skill.name,
          status: "configured" as const,
        }))
      : skills;

  // Display MCP servers from config snapshot (preferred) or runtime data
  const displayMcpServers =
    configuredMcpServers.length > 0
      ? configuredMcpServers.map((server) => ({
          server_name: server.name,
          status: "configured" as const,
        }))
      : visibleMcpStatuses;

  const displayPresets = configuredPresets.map((plugin) => ({
    id: String(plugin.id),
    name: plugin.name,
    status: "configured" as const,
  }));

  const getSkillStatusIcon = (status: string) => {
    if (status === "configured") {
      return <CheckCircle2 className="size-3 text-foreground" />;
    }
    switch (status) {
      case "completed":
        return <CheckCircle2 className="size-3 text-foreground" />;
      case "failed":
        return <XCircle className="size-3 text-muted-foreground/60" />;
      default:
        return <AlertCircle className="size-3 text-muted-foreground/80" />;
    }
  };

  const getMcpStatusIcon = (status: string) => {
    if (status === "configured") {
      return <CheckCircle2 className="size-3 text-foreground" />;
    }
    switch (status) {
      case "connected":
        return <CheckCircle2 className="size-3 text-foreground" />;
      case "disconnected":
        return <XCircle className="size-3 text-muted-foreground/60" />;
      default:
        return <AlertCircle className="size-3 text-muted-foreground/80" />;
    }
  };

  return (
    <div
      className={cn(
        "flex min-w-0 flex-wrap items-center gap-2 overflow-hidden px-4 py-2.5",
        className,
      )}
    >
      <TooltipProvider delayDuration={200}>
        {/* Browser Card */}
        {hasBrowser && (
          <div className="group flex min-w-0 max-w-full items-center gap-2 rounded-lg border border-border/60 bg-card px-3 py-2 transition-all hover:border-border hover:shadow-sm cursor-pointer">
            <AppWindow className="size-3.5 text-foreground group-hover:text-foreground/80 transition-colors" />
            <span className="min-w-0 truncate text-xs font-medium text-foreground">
              {t("chat.statusBar.browser")}
            </span>
            <Badge
              variant="secondary"
              className="text-xs h-5 px-1.5 bg-muted text-foreground"
            >
              {t("common.enabled")}
            </Badge>
          </div>
        )}

        {/* Skills Card */}
        {hasSkills &&
          renderInteractiveCard(
            <div className="group flex min-w-0 max-w-full items-center gap-2 rounded-lg border border-border/60 bg-card px-3 py-2 transition-all hover:border-border hover:shadow-sm cursor-pointer">
              <Zap className="size-3.5 text-foreground group-hover:text-foreground/80 transition-colors" />
              <span className="min-w-0 truncate text-xs font-medium text-foreground">
                {configuredSkills.length > 0
                  ? t("chat.statusBar.skillsConfigured")
                  : t("chat.statusBar.skillsUsed")}
              </span>
              <Badge
                variant="secondary"
                className="text-xs h-5 px-1.5 bg-muted text-foreground"
              >
                {displaySkills.length}
              </Badge>
            </div>,
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
              {displaySkills.map((skill) => (
                <div
                  key={skill.id}
                  className="flex items-center gap-2 text-sm px-1"
                >
                  {getSkillStatusIcon(skill.status)}
                  <span className="text-foreground">{skill.name}</span>
                </div>
              ))}
            </div>,
          )}

        {/* Presets Card */}
        {hasPresets && (
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="group flex min-w-0 max-w-full items-center gap-2 rounded-lg border border-border/60 bg-card px-3 py-2 transition-all hover:border-border hover:shadow-sm cursor-pointer">
                <Plug className="size-3.5 text-foreground group-hover:text-foreground/80 transition-colors" />
                <span className="min-w-0 truncate text-xs font-medium text-foreground">
                  {t("chat.statusBar.pluginsConfigured")}
                </span>
                <Badge
                  variant="secondary"
                  className="text-xs h-5 px-1.5 bg-muted text-foreground"
                >
                  {displayPresets.length}
                </Badge>
              </div>
            </TooltipTrigger>
            <TooltipContent
              side="top"
              className="p-2 bg-card border-border shadow-lg"
              sideOffset={8}
            >
              <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
                {displayPresets.map((plugin) => (
                  <div
                    key={plugin.id}
                    className="flex items-center gap-2 text-sm px-1"
                  >
                    {getSkillStatusIcon(plugin.status)}
                    <span className="text-foreground">{plugin.name}</span>
                  </div>
                ))}
              </div>
            </TooltipContent>
          </Tooltip>
        )}

        {/* MCP Card */}
        {hasMcp &&
          renderInteractiveCard(
            <div className="group flex min-w-0 max-w-full items-center gap-2 rounded-lg border border-border/60 bg-card px-3 py-2 transition-all hover:border-border hover:shadow-sm cursor-pointer">
              <Server className="size-3.5 text-foreground group-hover:text-foreground/80 transition-colors" />
              <span className="min-w-0 truncate text-xs font-medium text-foreground">
                {configuredMcpServers.length > 0
                  ? t("chat.statusBar.mcpConfigured")
                  : t("chat.statusBar.mcp")}
              </span>
              <Badge
                variant="secondary"
                className="text-xs h-5 px-1.5 bg-muted text-foreground"
              >
                {displayMcpServers.length}
              </Badge>
            </div>,
            <div className="space-y-1.5 max-h-[200px] overflow-y-auto">
              {displayMcpServers.map((mcp, index) => (
                <div
                  key={index}
                  className="flex items-center gap-2 text-sm px-1"
                >
                  {getMcpStatusIcon(mcp.status)}
                  <span className="text-foreground font-mono">
                    {mcp.server_name}
                  </span>
                </div>
              ))}
            </div>,
          )}
      </TooltipProvider>
    </div>
  );
}
