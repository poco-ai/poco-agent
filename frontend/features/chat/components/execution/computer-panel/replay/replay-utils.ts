import type { ToolExecutionResponse } from "@/features/chat/types";

export const POCO_PLAYWRIGHT_MCP_PREFIX = "mcp____poco_playwright__";
export const COMPUTER_GENERIC_TOOL_NAMES = new Set([
  "edit",
  "read",
  "write",
  "glob",
  "grep",
]);

export function truncateMiddle(value: string, maxLen: number): string {
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

export function normalizeToolName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[\s_-]/g, "");
}

export function getGenericToolSummary(
  execution: ToolExecutionResponse,
): string | null {
  const normalizedToolName = normalizeToolName(execution.tool_name || "");
  const input = execution.tool_input || {};

  if (normalizedToolName === "edit") {
    return pickFirstString(input, [
      "file_path",
      "path",
      "old_string",
      "new_string",
    ]);
  }
  if (normalizedToolName === "read") {
    return pickFirstString(input, ["file_path", "path"]);
  }
  if (normalizedToolName === "write") {
    return pickFirstString(input, ["file_path", "path"]);
  }
  if (normalizedToolName === "glob") {
    return pickFirstString(input, ["pattern", "path"]);
  }
  if (normalizedToolName === "grep") {
    return pickFirstString(input, ["pattern", "path", "glob", "type"]);
  }
  return null;
}

export function getBrowserStepLabel(execution: ToolExecutionResponse): string {
  const name = execution.tool_name || "";
  if (!name.startsWith(POCO_PLAYWRIGHT_MCP_PREFIX)) return name;
  const rawTool = name.slice(POCO_PLAYWRIGHT_MCP_PREFIX.length).trim();
  const action = rawTool.startsWith("browser_")
    ? rawTool.slice("browser_".length)
    : rawTool;

  const input = execution.tool_input || {};
  const summary = (() => {
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

  const meta = summary ? ` - ${truncateMiddle(summary, 80)}` : "";
  return `${action}${meta}`;
}

export function clampIndex(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

export function getFrameAdvanceDelayMs(
  kind: "browser" | "terminal" | "tool",
): number {
  const baseMs = kind === "browser" ? 1200 : kind === "terminal" ? 1800 : 1500;
  return Math.max(80, baseMs);
}
