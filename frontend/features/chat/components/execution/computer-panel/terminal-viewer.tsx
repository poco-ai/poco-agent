"use client";

import * as React from "react";
import { CheckCircle2, XCircle } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import type { ToolExecutionResponse } from "@/features/chat/types";
import { SyntaxHighlighter } from "@/lib/markdown/prism";

type TerminalViewerProps = {
  execution: ToolExecutionResponse;
};

const terminalSyntaxTheme: Record<string, React.CSSProperties> = {
  'pre[class*="language-"]': {
    color: "var(--foreground)",
    background: "transparent",
  },
  'code[class*="language-"]': {
    color: "var(--foreground)",
    background: "transparent",
  },
  comment: {
    color: "var(--muted-foreground)",
    fontStyle: "italic",
  },
  punctuation: {
    color: "var(--muted-foreground)",
  },
  keyword: {
    color: "var(--primary)",
  },
  builtin: {
    color: "var(--primary)",
  },
  string: {
    color: "var(--primary)",
  },
  number: {
    color: "var(--chart-4)",
  },
  function: {
    color: "var(--chart-2)",
  },
  operator: {
    color: "var(--muted-foreground)",
  },
  variable: {
    color: "var(--foreground)",
  },
};

function parseBashResult(execution: ToolExecutionResponse): {
  output: string;
  exitCode?: number;
  killed?: boolean;
  shellId?: string | null;
} {
  const raw = execution.tool_output?.["content"];
  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw) as unknown;
      if (parsed && typeof parsed === "object") {
        const obj = parsed as Record<string, unknown>;
        const output = typeof obj["output"] === "string" ? obj["output"] : raw;
        const exitCode =
          typeof obj["exitCode"] === "number" ? obj["exitCode"] : undefined;
        const killed =
          typeof obj["killed"] === "boolean" ? obj["killed"] : undefined;
        const shellId =
          typeof obj["shellId"] === "string" ? obj["shellId"] : null;
        return { output, exitCode, killed, shellId };
      }
    } catch {
      // fall back to raw
    }
    return { output: raw };
  }
  if (raw === undefined || raw === null) return { output: "" };
  return { output: JSON.stringify(raw) };
}

function TerminalOutputSkeleton({ label }: { label: string }) {
  return (
    <SkeletonItem className="h-20 min-h-0 w-full">
      <span className="sr-only">{label}</span>
    </SkeletonItem>
  );
}

export function TerminalViewer({ execution }: TerminalViewerProps) {
  const { t } = useT("translation");
  const cmd =
    typeof execution.tool_input?.["command"] === "string"
      ? (execution.tool_input?.["command"] as string)
      : "";
  const isDone = Boolean(execution.tool_output);
  const isError = execution.is_error;
  const result = parseBashResult(execution);

  return (
    <div className="h-full w-full bg-card">
      <ScrollArea className="h-full">
        <div className="p-4 font-mono text-xs space-y-3 min-w-0 max-w-full">
          <div className="flex items-start gap-2">
            <span className="select-none text-muted-foreground">$</span>
            <div className="min-w-0 flex-1 max-w-full">
              {cmd ? (
                <SyntaxHighlighter
                  language="bash"
                  style={terminalSyntaxTheme}
                  wrapLongLines
                  customStyle={{
                    margin: 0,
                    padding: 0,
                    background: "transparent",
                    fontSize: "0.75rem",
                    fontWeight: 500,
                    lineHeight: "1.5",
                    whiteSpace: "pre-wrap",
                    overflowWrap: "anywhere",
                    wordBreak: "break-word",
                    maxWidth: "100%",
                  }}
                  codeTagProps={{
                    style: {
                      background: "transparent",
                      fontFamily: "inherit",
                    },
                  }}
                >
                  {cmd}
                </SyntaxHighlighter>
              ) : (
                <span className="text-muted-foreground">
                  {t("computer.terminal.unknownCommand")}
                </span>
              )}
            </div>
            <span className="shrink-0">
              {!isDone ? (
                <SkeletonCircle className="size-3.5" />
              ) : isError ? (
                <XCircle className="size-3.5 text-destructive" />
              ) : (
                <CheckCircle2 className="size-3.5 text-primary" />
              )}
            </span>
          </div>
          {isDone ? (
            <div
              className={cn(
                "rounded-md border bg-background p-3 text-foreground/85",
                "w-full min-w-0 max-w-full whitespace-pre-wrap break-all [overflow-wrap:anywhere]",
              )}
            >
              {result.output || (
                <span className="text-muted-foreground">
                  {t("computer.terminal.noOutput")}
                </span>
              )}
            </div>
          ) : (
            <TerminalOutputSkeleton label={t("computer.terminal.running")} />
          )}
          {isDone && typeof result.exitCode === "number" ? (
            <div
              className={cn(
                "text-[11px]",
                result.exitCode === 0
                  ? "text-muted-foreground"
                  : "text-destructive",
              )}
            >
              {t("computer.terminal.exitCode", {
                code: String(result.exitCode),
              })}
              {result.killed ? ` - ${t("computer.terminal.killed")}` : ""}
            </div>
          ) : null}
        </div>
      </ScrollArea>
    </div>
  );
}
