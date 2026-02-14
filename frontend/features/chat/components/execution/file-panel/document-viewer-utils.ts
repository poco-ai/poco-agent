import type { FileNode } from "@/features/chat/types";

export const DOC_VIEWER_TYPE_MAP: Record<string, string> = {
  bmp: "bmp",
  doc: "doc",
  docx: "docx",
  jpg: "jpg",
  jpeg: "jpg",
  pdf: "pdf",
  png: "png",
  ppt: "ppt",
  pptx: "pptx",
  tiff: "tiff",
  xls: "xls",
  xlsx: "xlsx",
};

export const DEFAULT_TEXT_LANGUAGE = "text";

const TEXT_LANGUAGE_MAP: Record<string, string> = {
  txt: "text",
  log: "text",
  csv: "text",
  md: "markdown",
  markdown: "markdown",
  mdown: "markdown",
  mdx: "markdown",
  py: "python",
  pyw: "python",
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
  json: "json",
  jsonc: "json",
  html: "markup",
  htm: "markup",
  xml: "markup",
  yml: "yaml",
  yaml: "yaml",
  sh: "bash",
  bash: "bash",
  zsh: "bash",
  css: "css",
  scss: "scss",
  less: "less",
  go: "go",
  java: "java",
  rb: "ruby",
  php: "php",
  swift: "swift",
  kt: "kotlin",
  kotlin: "kotlin",
  cs: "csharp",
  csharp: "csharp",
  c: "c",
  h: "c",
  cpp: "cpp",
  cxx: "cpp",
  hpp: "cpp",
  mm: "objectivec",
  m: "objectivec",
  ps1: "powershell",
  dockerfile: "docker",
  env: "ini",
  ini: "ini",
  cfg: "ini",
  conf: "ini",
  toml: "ini",
  properties: "ini",
  rs: "rust",
  cjs: "javascript",
  mjs: "javascript",
};

const MIME_LANGUAGE_RULES: Array<{ test: RegExp; language: string }> = [
  { test: /^application\/json/i, language: "json" },
  { test: /javascript/i, language: "javascript" },
  { test: /typescript/i, language: "typescript" },
  { test: /python/i, language: "python" },
  { test: /markdown/i, language: "markdown" },
  { test: /^text\/(plain|csv)/i, language: "text" },
  { test: /(shell|bash|zsh)/i, language: "bash" },
  { test: /(yaml|yml)/i, language: "yaml" },
  { test: /(html|xml)/i, language: "markup" },
  { test: /css/i, language: "css" },
  { test: /java/i, language: "java" },
  { test: /c\+\+/i, language: "cpp" },
  { test: /\bc\b/i, language: "c" },
  { test: /go/i, language: "go" },
  { test: /rust/i, language: "rust" },
  { test: /sql/i, language: "sql" },
];

export function ensureAbsoluteUrl(url?: string | null): string | undefined {
  if (!url) return undefined;
  if (
    url.startsWith("http") ||
    url.startsWith("blob:") ||
    url.startsWith("data:")
  ) {
    return url;
  }
  try {
    if (typeof window !== "undefined") {
      return new URL(url, window.location.origin).toString();
    }
    return url;
  } catch (error) {
    console.warn("[DocumentViewer] Failed to resolve URL", error);
    return url;
  }
}

export function extractExtension(file?: FileNode): string {
  if (!file) return "";
  const sources = [file.name, file.path, file.url].filter(Boolean) as string[];
  for (const source of sources) {
    const sanitized = source.split(/[?#]/)[0];
    const parts = sanitized.split(".");
    if (parts.length > 1) {
      const ext = parts.pop()?.toLowerCase();
      if (ext) return ext;
    }
  }
  return "";
}

export function getTextLanguage(
  ext: string,
  mime?: string | null,
): string | undefined {
  if (ext && TEXT_LANGUAGE_MAP[ext]) return TEXT_LANGUAGE_MAP[ext];
  if (mime) {
    const match = MIME_LANGUAGE_RULES.find(({ test }) => test.test(mime));
    if (match) return match.language;
    if (mime.startsWith("text/")) return DEFAULT_TEXT_LANGUAGE;
  }
  return undefined;
}
