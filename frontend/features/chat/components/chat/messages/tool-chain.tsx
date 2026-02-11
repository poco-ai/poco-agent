"use client";

import * as React from "react";
import {
  SquareTerminal,
  CheckCircle2,
  XCircle,
  Loader2,
  ChevronDown,
  ChevronRight,
  AppWindow,
  Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ToolUseBlock, ToolResultBlock } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";

interface ToolChainProps {
  blocks: (ToolUseBlock | ToolResultBlock)[];
  variant?: "tool" | "subagent";
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
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed) return trimmed;
    }
  }
  return null;
}

function isTaskSubagentStep(step: ToolStepPair): boolean {
  return step.use.name === "Task";
}

function ToolStep({ toolUse, toolResult, isOpen, onToggle }: ToolStepProps) {
  const { t } = useT("translation");
  const isCompleted = !!toolResult;
  const isError = toolResult?.is_error;
  const isLoading = !isCompleted;
  const isTaskTool = toolUse.name === "Task";
  const isSubagentTool = isTaskTool;

  const playwrightBrowserMeta = React.useMemo(() => {
    if (!toolUse.name.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) return null;

    const rawTool = toolUse.name
      .slice(POCO_PLAYWRIGHT_MCP_PREFIX.length)
      .trim();
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
      ]);
    })();

    return {
      toolName: rawTool,
      action,
      summary: summary ? truncateMiddle(summary, 80) : null,
    };
  }, [toolUse.input, toolUse.name]);

  const taskMeta = React.useMemo(() => {
    if (!isTaskTool) return null;
    const input = toolUse.input || {};
    const subagentType =
      typeof input["subagent_type"] === "string"
        ? input["subagent_type"]
        : typeof input["subagentType"] === "string"
          ? input["subagentType"]
          : "";
    return {
      subagentType: subagentType.trim(),
    };
  }, [isTaskTool, toolUse.input]);

  const outputText = React.useMemo(() => {
    if (!toolResult) return "";
    if (!isTaskTool) return toolResult.content;
    try {
      const parsed = JSON.parse(toolResult.content);
      if (
        parsed &&
        typeof parsed === "object" &&
        "result" in parsed &&
        typeof (parsed as { result?: unknown }).result === "string"
      ) {
        const result = (parsed as { result: string }).result.trim();
        if (result) return result;
      }
    } catch {
      // fall back to raw content
    }
    return toolResult.content;
  }, [isTaskTool, toolResult]);

  const toolLabel = playwrightBrowserMeta
    ? `${t("chat.statusBar.browser")} (${playwrightBrowserMeta.toolName})`
    : toolUse.name;
  const subagentName = taskMeta?.subagentType || toolUse.name;
  const toolDescription = playwrightBrowserMeta?.summary || null;

  return (
    <div className="border border-border/50 rounded-md bg-muted/30 overflow-hidden mb-2 last:mb-0">
      <Collapsible open={isOpen} onOpenChange={onToggle}>
        <CollapsibleTrigger className="flex items-center w-full p-2 hover:bg-muted/50 transition-colors gap-2 text-left">
          <div className="shrink-0">
            {isLoading ? (
              <Loader2 className="size-4 animate-spin text-primary" />
            ) : isError ? (
              <XCircle className="size-4 text-destructive" />
            ) : (
              <CheckCircle2 className="size-4 text-success" />
            )}
          </div>

          <div className="flex-1 min-w-0 flex items-center gap-2">
            {playwrightBrowserMeta ? (
              <AppWindow className="size-3.5 text-muted-foreground/80 shrink-0" />
            ) : isSubagentTool ? (
              <Bot className="size-3.5 text-muted-foreground/80 shrink-0" />
            ) : null}
            <span className="text-xs font-mono font-medium text-foreground truncate">
              {isSubagentTool ? subagentName : toolLabel}
            </span>
            {!isSubagentTool && toolDescription ? (
              <span className="text-[11px] text-muted-foreground truncate">
                {toolDescription}
              </span>
            ) : null}
          </div>

          <div className="shrink-0 flex items-center gap-2">
            {isLoading ? (
              <Badge
                variant="outline"
                className="h-4 px-1 text-[10px] bg-background text-muted-foreground rounded-sm border-transparent animate-pulse"
              >
                {t("status.running")}
              </Badge>
            ) : null}
            {isOpen ? (
              <ChevronDown className="size-3.5 text-muted-foreground" />
            ) : (
              <ChevronRight className="size-3.5 text-muted-foreground" />
            )}
          </div>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="p-2 pt-0 space-y-2 text-xs font-mono border-t border-border/50 bg-background/50">
            {/* Input */}
            <div className="mt-2">
              <div className="text-[10px] uppercase text-muted-foreground mb-1 select-none">
                {t("chat.input")}
              </div>
              <div className="bg-muted/50 p-2 rounded overflow-hidden text-foreground/90">
                <pre className="whitespace-pre-wrap break-all">
                  {JSON.stringify(toolUse.input, null, 2)}
                </pre>
              </div>
            </div>

            {/* Output */}
            {isCompleted && (
              <div>
                <div className="text-[10px] uppercase text-muted-foreground mb-1 select-none flex items-center gap-1">
                  {t("chat.output")}
                </div>
                <div
                  className={cn(
                    "p-2 rounded overflow-hidden text-foreground/90",
                    isError
                      ? "bg-destructive/10 text-destructive border border-destructive/20"
                      : "bg-muted/50",
                  )}
                >
                  <pre className="whitespace-pre-wrap break-all">
                    {outputText}
                  </pre>
                </div>
              </div>
            )}

            {toolUse.subagent_transcript &&
            toolUse.subagent_transcript.length > 0 ? (
              <div>
                <div className="text-[10px] uppercase text-muted-foreground mb-1 select-none">
                  {t("chat.subagentTranscript")}
                </div>
                <div className="bg-muted/50 p-2 rounded overflow-hidden text-foreground/90">
                  <pre className="whitespace-pre-wrap break-all">
                    {toolUse.subagent_transcript.join("\n\n")}
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

export function ToolChain({ blocks, variant = "tool" }: ToolChainProps) {
  const { t } = useT("translation");
  const [openStepId, setOpenStepId] = React.useState<string | null>(null);

  // Group blocks into steps (Use + Result pair)
  const steps = React.useMemo(() => {
    const result: ToolStepPair[] = [];

    // First pass: find all uses
    for (const block of blocks) {
      if (block._type === "ToolUseBlock") {
        result.push({ use: block });
      }
    }

    // Second pass: attach results
    for (const block of blocks) {
      if (block._type === "ToolResultBlock") {
        const step = result.find((s) => s.use.id === block.tool_use_id);
        if (step) {
          step.result = block;
        }
      }
    }
    return result;
  }, [blocks]);
  const isSubagentChain =
    variant === "subagent" || steps.every(isTaskSubagentStep);

  const isRunning = steps.some((s) => !s.result);
  // Initialize open if running, closed if completed (history)
  const [isExpanded, setIsExpanded] = React.useState(isRunning);
  const prevIsRunning = React.useRef(isRunning);

  // Auto-open the running step
  // Auto-open the running step logic removed per user request
  // React.useEffect(() => {
  //   const runningStep = steps.find((s) => !s.result);
  //   if (runningStep) {
  //     setOpenStepId(runningStep.use.id);
  //   }
  // }, [steps]);

  // Auto-expand when new tool call starts (do NOT auto-collapse when finished)
  React.useEffect(() => {
    // If we transitioned from not running to running (new tool call), auto-expand
    if (!prevIsRunning.current && isRunning) {
      setIsExpanded(true);
    }
    prevIsRunning.current = isRunning;
  }, [isRunning]);

  if (steps.length === 0) return null;

  return (
    <div className="w-full my-2 rounded-md border border-border/60 bg-muted/20 px-3 py-2">
      <Collapsible open={isExpanded} onOpenChange={setIsExpanded}>
        <CollapsibleTrigger className="flex items-center gap-2 w-full cursor-pointer select-none text-xs font-medium text-muted-foreground hover:text-foreground transition-colors group">
          <div className="flex items-center gap-1.5">
            {isSubagentChain ? (
              <Bot className="size-3.5" />
            ) : (
              <SquareTerminal className="size-3.5" />
            )}
            <span>
              {isSubagentChain
                ? t("chat.subagentExecution")
                : t("chat.toolExecution")}
            </span>
            {steps.length > 0 && (
              <span className="opacity-70">({steps.length})</span>
            )}
          </div>

          {/* Show little badges if collapsed */}
          {!isExpanded && (
            <div className="flex items-center gap-1 ml-auto">
              {/* Just show one badge to indicate status if not expanded */}
              {isRunning ? (
                <Loader2 className="size-3 animate-spin text-primary" />
              ) : (
                <CheckCircle2 className="size-3 text-success" />
              )}
            </div>
          )}
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="space-y-1 mt-2 border-t border-border/50 pt-2">
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
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
