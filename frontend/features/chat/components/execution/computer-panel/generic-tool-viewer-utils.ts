import type { ToolExecutionResponse } from "@/features/chat/types";

export const TOOL_NAME_TRANSLATION_KEY_MAP: Record<string, string> = {
  bash: "bash",
  edit: "edit",
  read: "read",
  write: "write",
  glob: "glob",
  grep: "grep",
};

export const CODE_THEME: Record<string, React.CSSProperties> = {
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

export function normalizeToolName(name: string): string {
  return name
    .trim()
    .toLowerCase()
    .replace(/[\s_-]/g, "");
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

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

export function stringifyForDisplay(value: unknown): string {
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function extractTextParts(value: unknown): string[] {
  if (typeof value === "string") return [value];

  if (Array.isArray(value)) {
    return value.flatMap((item) => extractTextParts(item));
  }

  if (!isRecord(value)) return [];

  const parts: string[] = [];
  if (typeof value.text === "string") parts.push(value.text);
  if (Array.isArray(value.content)) {
    parts.push(...extractTextParts(value.content));
  }
  return parts;
}

export function parseToolOutputPayload(
  execution: ToolExecutionResponse,
): unknown {
  const raw = execution.tool_output?.["content"];
  const textParts = extractTextParts(raw);
  if (textParts.length > 0) {
    const joined = textParts.join("\n").trim();
    if (joined) return parseJsonLike(joined);
  }
  return parseJsonLike(raw);
}

export function stripReadLineMarkers(text: string): string {
  const lineMarkerPattern = /^\s*\d+\s*(?:→|➜|->)\s?/;
  if (!lineMarkerPattern.test(text)) return text;
  return text
    .split("\n")
    .map((line) => line.replace(lineMarkerPattern, ""))
    .join("\n");
}

export function guessCodeLanguage(filePath?: string | null): string {
  if (!filePath) return "text";
  const extension = filePath.split(".").pop()?.toLowerCase();
  if (!extension) return "text";
  const map: Record<string, string> = {
    ts: "typescript",
    tsx: "tsx",
    js: "javascript",
    jsx: "jsx",
    py: "python",
    go: "go",
    rs: "rust",
    java: "java",
    c: "c",
    cpp: "cpp",
    h: "cpp",
    css: "css",
    html: "html",
    md: "markdown",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    toml: "toml",
    sh: "bash",
    zsh: "bash",
    sql: "sql",
    txt: "text",
  };
  return map[extension] ?? "text";
}
