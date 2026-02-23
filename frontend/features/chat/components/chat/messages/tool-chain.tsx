"use client";

import * as React from "react";
import {
  ChevronDown,
  ChevronRight,
  Loader2,
  Wrench,
  XCircle,
  CheckCircle2,
  Bot,
  MessageSquare,
  SquareTerminal,
  Pencil,
  PenSquare,
  FileText,
  Folder,
  Search,
  Notebook,
  Globe,
  Sparkles,
  ListTodo,
  History,
  ListChecks,
  Database,
  AppWindow,
  Server,
} from "lucide-react";
import type { ToolUseBlock, ToolResultBlock } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface ToolChainProps {
  blocks: (ToolUseBlock | ToolResultBlock)[];
  sessionStatus?: string;
}

interface ToolStepProps {
  toolUse: ToolUseBlock;
  toolResult?: ToolResultBlock;
  isOpen: boolean;
  onToggle: () => void;
}

type ToolStepPair = {
  use: ToolUseBlock;
  result?: ToolResultBlock;
};

const POCO_PLAYWRIGHT_MCP_PREFIX = "mcp____poco_playwright__";

type BrowserToolMeta = {
  action: string;
  summary: string | null;
};

type McpToolMeta = {
  server: string;
  action: string | null;
};

type SkillToolMeta = {
  name: string | null;
};

function parseJsonLike(value: unknown): unknown {
  if (typeof value !== "string") return value;
  const trimmed = value.trim();
  if (!trimmed) return "";
  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
}

function stringifyForDisplay(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function truncateMiddle(value: string, maxLen: number): string {
  const text = value.trim();
  if (text.length <= maxLen) return text;
  if (maxLen <= 8) return text.slice(0, maxLen);
  const head = Math.ceil((maxLen - 3) / 2);
  const tail = Math.floor((maxLen - 3) / 2);
  return `${text.slice(0, head)}...${text.slice(text.length - tail)}`;
}

function pickFirstString(
  input: Record<string, unknown> | null | undefined,
  keys: string[],
): string | null {
  if (!input) return null;
  for (const key of keys) {
    const value = input[key];
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function normalizeToolName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[\s_-]/g, "");
}

function prettifyMcpPart(value: string): string {
  return value
    .trim()
    .replace(/^_+|_+$/g, "")
    .replaceAll("_", " ");
}

function getGenericMcpToolMeta(toolName: string): McpToolMeta | null {
  const trimmed = toolName.trim();
  if (!trimmed.startsWith("mcp__")) return null;
  if (trimmed.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) return null;

  const body = trimmed.slice("mcp__".length);
  if (!body) return null;

  const parts = body.split("__").filter((part) => part.length > 0);
  if (parts.length === 0) return null;

  const server = prettifyMcpPart(parts[0] ?? "");
  const actionRaw = parts.slice(1).join("__");
  const action = prettifyMcpPart(actionRaw);

  return {
    server: server || "mcp",
    action: action || null,
  };
}

function getBrowserToolMeta(toolUse: ToolUseBlock): BrowserToolMeta | null {
  if (!toolUse.name.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) return null;

  const rawTool = toolUse.name.slice(POCO_PLAYWRIGHT_MCP_PREFIX.length).trim();
  if (!rawTool) return null;

  const action = rawTool.startsWith("browser_")
    ? rawTool.slice("browser_".length)
    : rawTool;

  const summary = (() => {
    const input = toolUse.input;
    if (action === "navigate") {
      return pickFirstString(input, ["url", "href"]);
    }
    if (action === "click" || action === "hover") {
      return pickFirstString(input, ["selector", "text", "role", "name"]);
    }
    if (action === "type" || action === "fill" || action === "press") {
      return (
        pickFirstString(input, ["selector", "role", "name", "text"]) ||
        pickFirstString(input, ["key", "value"])
      );
    }
    if (action === "screenshot") {
      return pickFirstString(input, ["path", "filename"]);
    }
    return pickFirstString(input, [
      "url",
      "selector",
      "text",
      "role",
      "name",
      "value",
      "query",
      "path",
      "key",
    ]);
  })();

  return {
    action,
    summary: summary ? truncateMiddle(summary, 100) : null,
  };
}

function getSkillToolMeta(toolUse: ToolUseBlock): SkillToolMeta | null {
  const normalizedName = normalizeToolName(toolUse.name || "");
  if (normalizedName !== "skill") return null;

  return {
    name: pickFirstString(toolUse.input, ["skill", "skill_name", "name"]),
  };
}

function renderToolIcon(toolName: string): React.ReactNode {
  if (toolName.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) {
    return <AppWindow className="size-3.5 text-muted-foreground" />;
  }
  if (getGenericMcpToolMeta(toolName)) {
    return <Server className="size-3.5 text-muted-foreground" />;
  }

  const normalized = normalizeToolName(toolName);
  switch (normalized) {
    case "skill":
      return <Sparkles className="size-3.5 text-muted-foreground" />;
    case "task":
      return <Bot className="size-3.5 text-muted-foreground" />;
    case "askuserquestion":
      return <MessageSquare className="size-3.5 text-muted-foreground" />;
    case "bash":
      return <SquareTerminal className="size-3.5 text-muted-foreground" />;
    case "edit":
      return <Pencil className="size-3.5 text-muted-foreground" />;
    case "read":
      return <FileText className="size-3.5 text-muted-foreground" />;
    case "write":
      return <PenSquare className="size-3.5 text-muted-foreground" />;
    case "glob":
      return <Folder className="size-3.5 text-muted-foreground" />;
    case "grep":
      return <Search className="size-3.5 text-muted-foreground" />;
    case "notebookedit":
      return <Notebook className="size-3.5 text-muted-foreground" />;
    case "webfetch":
    case "websearch":
      return <Globe className="size-3.5 text-muted-foreground" />;
    case "todowrite":
      return <ListTodo className="size-3.5 text-muted-foreground" />;
    case "bashoutput":
      return <History className="size-3.5 text-muted-foreground" />;
    case "killbash":
      return <XCircle className="size-3.5 text-muted-foreground" />;
    case "exitplanmode":
      return <ListChecks className="size-3.5 text-muted-foreground" />;
    case "listmcpresources":
    case "readmcpresource":
      return <Database className="size-3.5 text-muted-foreground" />;
    default:
      return <Wrench className="size-3.5 text-muted-foreground" />;
  }
}

function ToolStep({ toolUse, toolResult, isOpen, onToggle }: ToolStepProps) {
  const { t } = useT("translation");

  const state: "running" | "failed" | "completed" = !toolResult
    ? "running"
    : toolResult.is_error
      ? "failed"
      : "completed";

  const stateIcon =
    state === "running" ? (
      <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
    ) : state === "failed" ? (
      <XCircle className="size-3.5 text-destructive" />
    ) : (
      <CheckCircle2 className="size-3.5 text-primary" />
    );

  const inputText = React.useMemo(
    () => stringifyForDisplay(toolUse.input ?? {}),
    [toolUse.input],
  );

  const outputText = React.useMemo(() => {
    if (!toolResult) return "";
    const parsed = parseJsonLike(toolResult.content);
    const text = stringifyForDisplay(parsed);
    return text.trim() ? text : t("chat.toolCards.text.empty");
  }, [toolResult, t]);

  const browserMeta = React.useMemo(
    () => getBrowserToolMeta(toolUse),
    [toolUse],
  );
  const mcpMeta = React.useMemo(
    () => getGenericMcpToolMeta(toolUse.name || ""),
    [toolUse.name],
  );
  const skillMeta = React.useMemo(() => getSkillToolMeta(toolUse), [toolUse]);
  const toolLabel = React.useMemo(() => {
    if (browserMeta) {
      const action = browserMeta.action.replaceAll("_", " ");
      return `${t("chat.statusBar.browser")}（${action}）`;
    }
    if (mcpMeta) {
      if (mcpMeta.action) {
        return `MCP（${mcpMeta.server} / ${mcpMeta.action}）`;
      }
      return `MCP（${mcpMeta.server}）`;
    }
    if (skillMeta) {
      const base = (toolUse.name || "Skill").trim() || "Skill";
      if (skillMeta.name) {
        return `${base}（${skillMeta.name}）`;
      }
      return base;
    }
    return (toolUse.name || t("chat.toolCards.tools.tool")).trim();
  }, [browserMeta, mcpMeta, skillMeta, t, toolUse.name]);

  return (
    <div className="mb-2 min-w-0 max-w-full last:mb-0">
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <CollapsibleTrigger className="flex w-full min-w-0 max-w-full items-center gap-2 overflow-hidden rounded-[1.1rem] border border-border/60 bg-card/70 px-3 py-2.5 text-left transition-colors hover:bg-muted/50">
          <span className="flex size-6 shrink-0 items-center justify-center rounded-md border border-border/60 bg-muted/30">
            {renderToolIcon(toolUse.name || "")}
          </span>

          <div className="min-w-0 flex-1 overflow-hidden">
            <div className="truncate text-xs font-medium text-foreground">
              {toolLabel}
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <span
              className="inline-flex size-6 items-center justify-center"
              aria-label={state}
              title={state}
            >
              {stateIcon}
            </span>
            {isOpen ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            )}
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="mt-2 min-w-0 max-w-full overflow-hidden rounded-[1.1rem] border border-border/60 bg-muted/20 p-3 text-xs">
            <div className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">
              {t("chat.input")}
            </div>
            <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-border/60 bg-background/60 p-2">
              <pre className="whitespace-pre-wrap break-all font-mono text-xs text-foreground/90">
                {inputText}
              </pre>
            </div>

            {toolResult ? (
              <div className="mt-3">
                <div className="mb-2 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {t("chat.output")}
                </div>
                <div
                  className={cn(
                    "min-w-0 max-w-full overflow-hidden rounded-lg border p-2",
                    toolResult.is_error
                      ? "border-destructive/30 bg-destructive/5"
                      : "border-border/60 bg-background/60",
                  )}
                >
                  <pre className="whitespace-pre-wrap break-all font-mono text-xs text-foreground/90">
                    {outputText}
                  </pre>
                </div>
              </div>
            ) : null}
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

export function ToolChain({ blocks, sessionStatus }: ToolChainProps) {
  const { t } = useT("translation");
  const [openStepId, setOpenStepId] = React.useState<string | null>(null);

  const normalizedSessionStatus = (sessionStatus || "").trim().toLowerCase();
  const isTerminalSession = ["completed", "failed", "canceled"].includes(
    normalizedSessionStatus,
  );

  const terminalToolResultText = React.useMemo(() => {
    if (normalizedSessionStatus === "failed") return t("status.failed");
    if (normalizedSessionStatus === "canceled") return t("status.canceled");
    return t("status.completed");
  }, [normalizedSessionStatus, t]);

  const terminalToolResultIsError = React.useMemo(() => {
    if (!isTerminalSession) return false;
    return normalizedSessionStatus !== "completed";
  }, [isTerminalSession, normalizedSessionStatus]);

  const steps = React.useMemo(() => {
    const result: ToolStepPair[] = [];

    for (const block of blocks) {
      if (block._type === "ToolUseBlock") {
        result.push({ use: block });
      }
    }

    for (const block of blocks) {
      if (block._type === "ToolResultBlock") {
        const step = result.find((s) => s.use.id === block.tool_use_id);
        if (step) step.result = block;
      }
    }

    if (isTerminalSession) {
      for (const step of result) {
        if (step.result) continue;
        step.result = {
          _type: "ToolResultBlock",
          tool_use_id: step.use.id,
          content: terminalToolResultText,
          is_error: terminalToolResultIsError,
        };
      }
    }

    return result;
  }, [
    blocks,
    isTerminalSession,
    terminalToolResultIsError,
    terminalToolResultText,
  ]);

  if (steps.length === 0) return null;

  return (
    <div className="my-2 w-full min-w-0 max-w-full overflow-hidden">
      {steps.map((step) => (
        <ToolStep
          key={step.use.id}
          toolUse={step.use}
          toolResult={step.result}
          isOpen={openStepId === step.use.id}
          onToggle={() =>
            setOpenStepId(openStepId === step.use.id ? null : step.use.id)
          }
        />
      ))}
    </div>
  );
}
