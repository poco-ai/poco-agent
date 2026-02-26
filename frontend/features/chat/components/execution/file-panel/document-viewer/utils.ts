import * as React from "react";

import type { ExcalidrawInitialDataState } from "@excalidraw/excalidraw/types";

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

const VIDEO_EXTENSIONS = new Set(["mp4", "m4v", "mov", "webm", "ogv", "ogg"]);

export const DEFAULT_TEXT_LANGUAGE = "text";
export const NO_SOURCE_ERROR = "NO_SOURCE";
export const EXCALIDRAW_PARSE_ERROR = "EXCALIDRAW_PARSE_ERROR";
const DRAWIO_VIEWER_BASE_URL = "https://app.diagrams.net/?lightbox=1";
const DRAWIO_MAX_HASH_LENGTH = 1500000;

type FileContentState =
  | { status: "idle" | "loading" }
  | { status: "success"; content: string }
  | { status: "error"; code: "NO_SOURCE" | "FETCH_ERROR"; message?: string };

interface UseFileTextContentParams {
  file?: FileNode;
  fallbackUrl?: string;
}

export const useFileTextContent = ({
  file,
  fallbackUrl,
}: UseFileTextContentParams) => {
  const [state, setState] = React.useState<FileContentState>({
    status: "idle",
  });
  const [refreshKey, setRefreshKey] = React.useState(0);

  const refetch = React.useCallback(() => {
    setRefreshKey((key) => key + 1);
  }, []);

  React.useEffect(() => {
    if (!file) {
      setState({ status: "idle" });
      return;
    }

    let isMounted = true;
    const controller = new AbortController();

    const load = async () => {
      setState({ status: "loading" });
      try {
        let text: string | undefined;

        if (fallbackUrl) {
          const isSameOrigin =
            typeof window !== "undefined" &&
            new URL(fallbackUrl, window.location.origin).origin ===
              window.location.origin;

          const response = await fetch(fallbackUrl, {
            signal: controller.signal,
            credentials: isSameOrigin ? "include" : "omit",
          });
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
          }
          text = await response.text();
        } else {
          throw new Error(NO_SOURCE_ERROR);
        }

        if (!isMounted) return;
        setState({ status: "success", content: text ?? "" });
      } catch (error) {
        if (!isMounted || controller.signal.aborted) return;
        if (error instanceof Error && error.message === NO_SOURCE_ERROR) {
          setState({ status: "error", code: "NO_SOURCE" });
          return;
        }
        setState({
          status: "error",
          code: "FETCH_ERROR",
          message:
            error instanceof Error
              ? error.message
              : typeof error === "string"
                ? error
                : undefined,
        });
      }
    };

    void load();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [file, fallbackUrl, refreshKey]);

  return { state, refetch } as const;
};

export const ensureAbsoluteUrl = (url?: string | null) => {
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
};

export const isSameOriginUrl = (url: string) => {
  try {
    return (
      typeof window !== "undefined" &&
      new URL(url, window.location.origin).origin === window.location.origin
    );
  } catch {
    return false;
  }
};

const triggerDownload = (url: string, filename: string) => {
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export const downloadFileFromUrl = async ({
  url,
  filename,
}: {
  url?: string;
  filename: string;
}) => {
  const absoluteUrl = ensureAbsoluteUrl(url);
  if (!absoluteUrl) return;

  try {
    const response = await fetch(absoluteUrl, {
      credentials: isSameOriginUrl(absoluteUrl) ? "include" : "omit",
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);
    triggerDownload(blobUrl, filename);
    setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
  } catch (error) {
    console.warn(
      "[DocumentViewer] Failed to download as blob, fallback to direct URL",
      error,
    );
    triggerDownload(absoluteUrl, filename);
  }
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export const parseExcalidrawScene = (
  content: string,
): ExcalidrawInitialDataState => {
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch {
    throw new Error(EXCALIDRAW_PARSE_ERROR);
  }

  if (!isRecord(parsed) || !Array.isArray(parsed.elements)) {
    throw new Error(EXCALIDRAW_PARSE_ERROR);
  }

  const scene: ExcalidrawInitialDataState = {
    elements: parsed.elements as ExcalidrawInitialDataState["elements"],
  };

  if (isRecord(parsed.appState)) {
    scene.appState = parsed.appState as ExcalidrawInitialDataState["appState"];
  }

  if (isRecord(parsed.files)) {
    scene.files = parsed.files as ExcalidrawInitialDataState["files"];
  }

  if (Array.isArray(parsed.libraryItems)) {
    scene.libraryItems =
      parsed.libraryItems as ExcalidrawInitialDataState["libraryItems"];
  }

  return scene;
};

export const extractExtension = (file?: FileNode) => {
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
};

export const getTextLanguage = (ext: string, mime?: string | null) => {
  if (ext && TEXT_LANGUAGE_MAP[ext]) return TEXT_LANGUAGE_MAP[ext];
  if (mime) {
    const match = MIME_LANGUAGE_RULES.find(({ test }) => test.test(mime));
    if (match) return match.language;
    if (mime.startsWith("text/")) return DEFAULT_TEXT_LANGUAGE;
  }
  return undefined;
};

export const isExcalidrawFile = (ext: string, mime?: string | null) =>
  ext === "excalidraw" || /excalidraw/i.test(mime ?? "");

export const isDrawioFile = (ext: string, mime?: string | null) =>
  ext === "drawio" ||
  /(?:vnd\.jgraph\.mxfile|drawio|diagrams\.net)/i.test(mime ?? "");

export const isVideoFile = (ext: string, mime?: string | null) =>
  VIDEO_EXTENSIONS.has(ext) || /^video\//i.test(mime ?? "");

export const buildDrawioViewerUrl = ({
  file,
  sourceUrl,
  rawData,
}: {
  file: FileNode;
  sourceUrl?: string;
  rawData?: string;
}) => {
  const title = file.name || file.path || "diagram.drawio";
  const searchParams = new URLSearchParams({
    title,
  });
  const prefix = `${DRAWIO_VIEWER_BASE_URL}&${searchParams.toString()}`;

  if (typeof rawData === "string") {
    const normalizedRaw = rawData.replace(/^\uFEFF/, "").trim();
    const encodedRaw = encodeURIComponent(normalizedRaw);
    if (encodedRaw.length <= DRAWIO_MAX_HASH_LENGTH) {
      return `${prefix}#R${encodedRaw}`;
    }
  }

  if (!sourceUrl) return undefined;
  return `${prefix}#U${encodeURIComponent(sourceUrl)}`;
};
