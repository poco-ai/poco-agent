"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import type { FileNode } from "@/features/chat/types";
import {
  File,
  Download,
  ExternalLink,
  Check,
  Copy,
  ChevronLeft,
  Maximize2,
  X,
} from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import type { DocViewerProps } from "react-doc-viewer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import remarkMath from "remark-math";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { MarkdownCode, MarkdownPre } from "@/components/shared/markdown-code";
import { SyntaxHighlighter, oneDark, oneLight } from "@/lib/markdown/prism";
import { SkeletonItem } from "@/components/ui/skeleton-shimmer";
import rehypeKatex from "rehype-katex";
import type { ExcalidrawInitialDataState } from "@excalidraw/excalidraw/types";
import type { ExcalidrawViewerClientProps } from "./excalidraw-viewer-client";

const dispatchCloseViewer = () => {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("close-document-viewer"));
};

const DocViewer = dynamic<DocViewerProps>(
  () => import("./doc-viewer-client").then((m) => m.DocViewerClient),
  {
    ssr: false,
    loading: () => {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const { t } = useT("translation");
      return (
        <DocumentViewerSkeleton label={t("artifacts.viewer.loadingEngine")} />
      );
    },
  },
);

const ExcalidrawViewer = dynamic<ExcalidrawViewerClientProps>(
  () =>
    import("./excalidraw-viewer-client").then((m) => m.ExcalidrawViewerClient),
  {
    ssr: false,
    loading: () => {
      // eslint-disable-next-line react-hooks/rules-of-hooks
      const { t } = useT("translation");
      return (
        <DocumentViewerSkeleton label={t("artifacts.viewer.loadingEngine")} />
      );
    },
  },
);

const DOC_VIEWER_TYPE_MAP: Record<string, string> = {
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

type XMindEmbedViewerInstance = {
  load: (file: ArrayBuffer) => void;
  setStyles?: (styles: Record<string, string>) => void;
  addEventListener?: (
    event: string,
    handler: (payload: unknown) => void,
  ) => void;
  removeEventListener?: (
    event: string,
    handler: (payload: unknown) => void,
  ) => void;
  setFitMap?: () => void;
  setZoomScale?: (scale: number) => void;
  switchSheet?: (sheetId: string) => void;
};

type XMindEmbedViewerConstructor = new (options: {
  el: string | HTMLElement | HTMLIFrameElement;
  region?: "cn" | "global";
  styles?: Record<string, string>;
  isPitchModeDisabled?: boolean;
}) => XMindEmbedViewerInstance;

declare global {
  interface Window {
    XMindEmbedViewer?: XMindEmbedViewerConstructor;
  }
}

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

const VIEW_CLASSNAME =
  "h-full w-full max-h-full animate-in fade-in duration-300 [--tw-enter-opacity:1] [--tw-enter-scale:1] [--tw-enter-translate-x:0] [--tw-enter-translate-y:0] overflow-hidden flex flex-col min-h-0";

function DocumentViewerSkeleton({ label }: { label: string }) {
  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "items-center justify-center p-6 text-muted-foreground",
      )}
    >
      <div className="w-full max-w-3xl space-y-3">
        <SkeletonItem className="h-10 min-h-0 w-1/3" />
        <SkeletonItem className="h-56 min-h-0 w-full" />
        <SkeletonItem className="h-10 min-h-0 w-2/3" />
      </div>
      <span className="sr-only">{label}</span>
    </div>
  );
}

function DocumentViewerOverlaySkeleton({ label }: { label: string }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center bg-background/70">
      <div className="w-full max-w-md space-y-3 px-6">
        <SkeletonItem className="h-10 min-h-0 w-2/3" />
        <SkeletonItem className="h-32 min-h-0 w-full" />
      </div>
      <span className="sr-only">{label}</span>
    </div>
  );
}

const DEFAULT_TEXT_LANGUAGE = "text";
const NO_SOURCE_ERROR = "NO_SOURCE";
const EXCALIDRAW_PARSE_ERROR = "EXCALIDRAW_PARSE_ERROR";
const DRAWIO_VIEWER_BASE_URL = "https://app.diagrams.net/?lightbox=1";
const DRAWIO_MAX_HASH_LENGTH = 1500000;
const XMIND_SCRIPT_SRC =
  "https://unpkg.com/xmind-embed-viewer/dist/umd/xmind-embed-viewer.js";

let xmindScriptPromise: Promise<void> | null = null;

type FileContentState =
  | { status: "idle" | "loading" }
  | { status: "success"; content: string }
  | { status: "error"; code: "NO_SOURCE" | "FETCH_ERROR"; message?: string };

interface UseFileTextContentParams {
  file?: FileNode;
  fallbackUrl?: string;
}

const useFileTextContent = ({
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

const ensureAbsoluteUrl = (url?: string | null) => {
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

const ensureXMindScript = () => {
  if (typeof window === "undefined") return Promise.resolve();
  if (window.XMindEmbedViewer) return Promise.resolve();

  if (!xmindScriptPromise) {
    xmindScriptPromise = new Promise((resolve, reject) => {
      const existingScript = document.querySelector(
        `script[src="${XMIND_SCRIPT_SRC}"]`,
      ) as HTMLScriptElement | null;

      if (existingScript) {
        existingScript.addEventListener("load", () => resolve());
        existingScript.addEventListener("error", () =>
          reject(new Error("Failed to load XMind viewer script")),
        );
        return;
      }

      const script = document.createElement("script");
      script.src = XMIND_SCRIPT_SRC;
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () =>
        reject(new Error("Failed to load XMind viewer script"));
      document.head.appendChild(script);
    });
  }

  return xmindScriptPromise;
};

const isSameOriginUrl = (url: string) => {
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

const downloadFileFromUrl = async ({
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

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null;

const parseExcalidrawScene = (content: string): ExcalidrawInitialDataState => {
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

const extractExtension = (file?: FileNode) => {
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

const getTextLanguage = (ext: string, mime?: string | null) => {
  if (ext && TEXT_LANGUAGE_MAP[ext]) return TEXT_LANGUAGE_MAP[ext];
  if (mime) {
    const match = MIME_LANGUAGE_RULES.find(({ test }) => test.test(mime));
    if (match) return match.language;
    if (mime.startsWith("text/")) return DEFAULT_TEXT_LANGUAGE;
  }
  return undefined;
};

const isExcalidrawFile = (ext: string, mime?: string | null) =>
  ext === "excalidraw" || /excalidraw/i.test(mime ?? "");

const isDrawioFile = (ext: string, mime?: string | null) =>
  ext === "drawio" ||
  /(?:vnd\.jgraph\.mxfile|drawio|diagrams\.net)/i.test(mime ?? "");

const buildDrawioViewerUrl = ({
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

interface ViewerToolbarProps {
  file: FileNode;
  subtitle?: string;
  resolvedUrl?: string;
  onClose?: () => void;
  onDownload?: () => void | Promise<void>;
  onCopy?: () => void;
  copyDisabled?: boolean;
  copyState?: "idle" | "copied";
  onOpenPreviewWindow?: () => void;
}

const TOOLBAR_ICON_BUTTON_CLASS =
  "h-8 w-8 rounded-md bg-transparent transition-colors hover:bg-accent/60 active:bg-accent/80";

const DocumentViewerToolbar = ({
  file,
  subtitle,
  resolvedUrl,
  onClose,
  onDownload,
  onCopy,
  copyDisabled,
  copyState = "idle",
  onOpenPreviewWindow,
}: ViewerToolbarProps) => {
  const { t } = useT("translation");

  return (
    <div className="w-full border-b px-3 py-2 text-xs text-muted-foreground sm:px-4 overflow-hidden">
      <div className="flex items-center gap-3 min-w-0 overflow-hidden">
        <Button
          size="icon"
          variant="ghost"
          className={
            onClose
              ? "group relative h-3 w-3 shrink-0 rounded-full bg-destructive p-0 transition-colors focus-visible:ring-0 focus-visible:border-transparent focus-visible:outline-none"
              : `${TOOLBAR_ICON_BUTTON_CLASS} shrink-0`
          }
          onClick={onClose ?? dispatchCloseViewer}
          aria-label={t("common.close")}
        >
          {onClose ? (
            <span
              aria-hidden
              className="pointer-events-none absolute inset-0 flex items-center justify-center"
            >
              <X
                className="size-[9px] text-muted-foreground opacity-0 transition-opacity duration-150 group-hover:opacity-100"
                strokeWidth={2.75}
              />
            </span>
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <span
            className="text-sm font-medium text-foreground min-w-0 max-w-full truncate overflow-hidden"
            title={file.name || file.path}
          >
            {file.name || file.path}
          </span>
          {subtitle && (
            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
              {subtitle}
            </span>
          )}
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          {onCopy && (
            <Button
              size="icon"
              variant="ghost"
              className={TOOLBAR_ICON_BUTTON_CLASS}
              onClick={onCopy}
              disabled={copyDisabled}
            >
              {copyState === "copied" ? (
                <Check className="size-4" />
              ) : (
                <Copy className="size-4" />
              )}
            </Button>
          )}
          {resolvedUrl && (
            <Button
              size="icon"
              variant="ghost"
              className={TOOLBAR_ICON_BUTTON_CLASS}
              onClick={() => {
                if (onDownload) {
                  void onDownload();
                  return;
                }
                void downloadFileFromUrl({
                  url: resolvedUrl,
                  filename: file.name || file.path || "document",
                });
              }}
            >
              <Download className="size-4" />
            </Button>
          )}
          {onOpenPreviewWindow && (
            <Button
              size="icon"
              variant="ghost"
              className={TOOLBAR_ICON_BUTTON_CLASS}
              onClick={onOpenPreviewWindow}
              aria-label={t("fileChange.previewFile")}
              title={t("fileChange.previewFile")}
            >
              <Maximize2 className="size-4" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

interface TextDocumentViewerProps {
  file: FileNode;
  language?: string;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}

const TextDocumentViewer = ({
  file,
  language = DEFAULT_TEXT_LANGUAGE,
  resolvedUrl,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: TextDocumentViewerProps) => {
  const { t } = useT("translation");
  const { resolvedTheme } = useTheme();
  const { state, refetch } = useFileTextContent({
    file,
    fallbackUrl: resolvedUrl,
  });
  const [copyState, setCopyState] = React.useState<"idle" | "copied">("idle");
  const syntaxLanguage =
    language && language !== DEFAULT_TEXT_LANGUAGE ? language : undefined;
  const subtitle = (language || DEFAULT_TEXT_LANGUAGE).toUpperCase();
  const syntaxTheme = resolvedTheme === "dark" ? oneDark : oneLight;

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  const handleCopy = React.useCallback(async () => {
    if (state.status !== "success") return;
    try {
      await navigator.clipboard.writeText(state.content);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1500);
    } catch (error) {
      console.error("[DocumentViewer] Copy failed", error);
    }
  }, [state]);

  if (state.status === "idle" || state.status === "loading") {
    return <DocumentViewerSkeleton label={t("artifacts.viewer.loadingDoc")} />;
  }

  if (state.status === "error") {
    const isSourceError = state.code === "NO_SOURCE";
    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isSourceError
              ? t("artifacts.viewer.notSupported")
              : t("artifacts.viewer.fetchError")
          }
          desc={isSourceError ? file.name : state.message}
          action={
            !isSourceError && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  if (ensureFreshFile) {
                    void ensureFreshFile(file);
                    return;
                  }
                  refetch();
                }}
              >
                {t("artifacts.viewer.retry")}
              </Button>
            )
          }
        />
      </div>
    );
  }

  if (state.status !== "success") {
    return null;
  }

  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
      )}
    >
      <DocumentViewerToolbar
        file={file}
        subtitle={subtitle}
        resolvedUrl={resolvedUrl}
        onClose={onClose}
        onDownload={handleDownload}
        onCopy={handleCopy}
        copyDisabled={false}
        copyState={copyState}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
      <div className="flex-1 overflow-auto min-h-0 p-4">
        <SyntaxHighlighter
          language={syntaxLanguage}
          style={syntaxTheme}
          wrapLines={false}
          showLineNumbers
          lineNumberStyle={{
            userSelect: "none",
            WebkitUserSelect: "none",
            minWidth: "2.5em",
            paddingRight: "1em",
            textAlign: "right",
            opacity: 0.5,
          }}
          customStyle={{
            background: "transparent",
            margin: 0,
            padding: 0,
            fontSize: "0.85rem",
            overflow: "visible",
          }}
          codeTagProps={{
            style: {
              background: "transparent",
            },
          }}
          PreTag={({ children, ...props }) => (
            <pre
              {...props}
              style={{
                background: "transparent",
                margin: 0,
                overflow: "visible",
              }}
            >
              {children}
            </pre>
          )}
        >
          {state.content}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

const MarkdownDocumentViewer = ({
  file,
  resolvedUrl,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: {
  file: FileNode;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}) => {
  const { t } = useT("translation");
  const { state, refetch } = useFileTextContent({
    file,
    fallbackUrl: resolvedUrl,
  });
  const [copyState, setCopyState] = React.useState<"idle" | "copied">("idle");

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  const handleCopy = React.useCallback(async () => {
    if (state.status !== "success") return;
    try {
      await navigator.clipboard.writeText(state.content);
      setCopyState("copied");
      setTimeout(() => setCopyState("idle"), 1500);
    } catch (error) {
      console.error("[DocumentViewer] Copy markdown failed", error);
    }
  }, [state]);

  if (state.status === "idle" || state.status === "loading") {
    return <DocumentViewerSkeleton label={t("artifacts.viewer.loadingDoc")} />;
  }

  if (state.status === "error") {
    const isSourceError = state.code === "NO_SOURCE";
    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isSourceError
              ? t("artifacts.viewer.notSupported")
              : t("artifacts.viewer.fetchError")
          }
          desc={isSourceError ? file.name : state.message}
          action={
            !isSourceError && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  if (ensureFreshFile) {
                    void ensureFreshFile(file);
                    return;
                  }
                  refetch();
                }}
              >
                {t("artifacts.viewer.retry")}
              </Button>
            )
          }
        />
      </div>
    );
  }

  if (state.status !== "success") {
    return null;
  }

  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
      )}
    >
      <DocumentViewerToolbar
        file={file}
        subtitle="MARKDOWN"
        resolvedUrl={resolvedUrl}
        onClose={onClose}
        onDownload={handleDownload}
        onCopy={handleCopy}
        copyDisabled={false}
        copyState={copyState}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
      <div className="flex-1 overflow-auto bg-background min-h-0">
        <div className="mx-auto w-full max-w-4xl px-6 py-8">
          <div className="prose prose-sm dark:prose-invert max-w-none break-words [&_*]:break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={{
                pre: MarkdownPre,
                code: MarkdownCode,
                a: ({ children, href, ...props }) => (
                  <a
                    className="text-primary underline underline-offset-4 decoration-primary/30 hover:decoration-primary"
                    target="_blank"
                    rel="noopener noreferrer"
                    href={href}
                    {...props}
                  >
                    {children}
                  </a>
                ),
                h1: ({ children }) => (
                  <h1 className="text-3xl font-bold mb-6 pb-2 border-b border-border">
                    {children}
                  </h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-2xl font-semibold mb-4 mt-8">
                    {children}
                  </h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-xl font-semibold mb-3 mt-6">
                    {children}
                  </h3>
                ),
                table: ({ children }) => (
                  <div className="overflow-x-auto my-6 rounded-lg border border-border">
                    <table className="w-full border-collapse text-sm">
                      {children}
                    </table>
                  </div>
                ),
                thead: ({ children }) => (
                  <thead className="bg-muted/50">{children}</thead>
                ),
                tbody: ({ children }) => (
                  <tbody className="divide-y divide-border">{children}</tbody>
                ),
                th: ({ children }) => (
                  <th className="border-b-2 border-border px-4 py-3 text-left font-semibold text-foreground">
                    {children}
                  </th>
                ),
                td: ({ children }) => (
                  <td className="px-4 py-3 text-foreground">{children}</td>
                ),
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-primary/20 bg-primary/5 pl-4 py-1 italic my-6 rounded-r-sm">
                    {children}
                  </blockquote>
                ),
                hr: () => <hr className="my-8 border-t border-border/60" />,
              }}
            >
              {state.content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

const ExcalidrawDocumentViewer = ({
  file,
  resolvedUrl,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: {
  file: FileNode;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}) => {
  const { t } = useT("translation");
  const { resolvedTheme } = useTheme();
  const { state, refetch } = useFileTextContent({
    file,
    fallbackUrl: resolvedUrl,
  });

  const parsedSceneState = React.useMemo(() => {
    if (state.status !== "success") {
      return { status: "idle" as const };
    }

    try {
      return {
        status: "success" as const,
        scene: parseExcalidrawScene(state.content),
      };
    } catch (error) {
      return {
        status: "error" as const,
        message: error instanceof Error ? error.message : undefined,
      };
    }
  }, [state]);

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  if (state.status === "idle" || state.status === "loading") {
    return <DocumentViewerSkeleton label={t("artifacts.viewer.loadingDoc")} />;
  }

  if (state.status === "error") {
    const isSourceError = state.code === "NO_SOURCE";
    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isSourceError
              ? t("artifacts.viewer.notSupported")
              : t("artifacts.viewer.fetchError")
          }
          desc={isSourceError ? file.name : state.message}
          action={
            !isSourceError && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  if (ensureFreshFile) {
                    void ensureFreshFile(file);
                    return;
                  }
                  refetch();
                }}
              >
                {t("artifacts.viewer.retry")}
              </Button>
            )
          }
        />
      </div>
    );
  }

  if (parsedSceneState.status === "error") {
    const isParseError = parsedSceneState.message === EXCALIDRAW_PARSE_ERROR;

    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isParseError
              ? t("artifacts.viewer.parseError")
              : t("artifacts.viewer.fetchError")
          }
          desc={file.name}
          action={
            <Button
              variant="outline"
              size="sm"
              className="mt-4"
              onClick={() => {
                refetch();
              }}
            >
              {t("artifacts.viewer.retry")}
            </Button>
          }
        />
      </div>
    );
  }

  if (parsedSceneState.status !== "success") {
    return null;
  }

  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
      )}
    >
      <DocumentViewerToolbar
        file={file}
        subtitle="EXCALIDRAW"
        resolvedUrl={resolvedUrl}
        onClose={onClose}
        onDownload={handleDownload}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
      <div className="flex-1 min-h-0 overflow-hidden bg-background">
        <ExcalidrawViewer
          initialData={parsedSceneState.scene}
          theme={resolvedTheme === "dark" ? "dark" : "light"}
        />
      </div>
    </div>
  );
};

const DrawioDocumentViewer = ({
  file,
  resolvedUrl,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: {
  file: FileNode;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}) => {
  const { t } = useT("translation");
  const { state, refetch } = useFileTextContent({
    file,
    fallbackUrl: resolvedUrl,
  });

  const viewerUrl =
    state.status === "success"
      ? buildDrawioViewerUrl({
          file,
          sourceUrl: resolvedUrl,
          rawData: state.content,
        })
      : undefined;

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  if (state.status === "idle" || state.status === "loading") {
    return <DocumentViewerSkeleton label={t("artifacts.viewer.loadingDoc")} />;
  }

  if (state.status === "error") {
    const isSourceError = state.code === "NO_SOURCE";
    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isSourceError
              ? t("artifacts.viewer.notSupported")
              : t("artifacts.viewer.fetchError")
          }
          desc={isSourceError ? file.name : state.message}
          action={
            !isSourceError && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  if (ensureFreshFile) {
                    void ensureFreshFile(file);
                    return;
                  }
                  refetch();
                }}
              >
                {t("artifacts.viewer.retry")}
              </Button>
            )
          }
        />
      </div>
    );
  }

  if (!viewerUrl) {
    return (
      <StatusLayout
        icon={File}
        title={t("artifacts.viewer.notSupported")}
        desc={file.name}
      />
    );
  }

  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
      )}
    >
      <DocumentViewerToolbar
        file={file}
        subtitle="DRAWIO"
        resolvedUrl={resolvedUrl}
        onClose={onClose}
        onDownload={handleDownload}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
      <iframe
        src={viewerUrl}
        className="h-full w-full border-0 bg-background"
        title={file.name || file.path || "drawio-diagram"}
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
      />
    </div>
  );
};

const XMindDocumentViewer = ({
  file,
  resolvedUrl,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: {
  file: FileNode;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}) => {
  const { t } = useT("translation");
  const containerRef = React.useRef<HTMLDivElement | null>(null);
  const viewerRef = React.useRef<XMindEmbedViewerInstance | null>(null);
  const loadIdRef = React.useRef(0);
  const [status, setStatus] = React.useState<"loading" | "ready" | "error">(
    "loading",
  );
  const [errorMessage, setErrorMessage] = React.useState<string | undefined>();
  const [refreshKey, setRefreshKey] = React.useState(0);

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  React.useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();
    const loadId = loadIdRef.current + 1;
    loadIdRef.current = loadId;

    const load = async () => {
      console.info("[XMindViewer] init", {
        name: file.name,
        path: file.path,
        url: file.url,
      });
      setStatus("loading");
      setErrorMessage(undefined);
      try {
        await ensureXMindScript();
        if (!isMounted || loadIdRef.current !== loadId) return;

        const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
        const url = ensureAbsoluteUrl(refreshed?.url ?? resolvedUrl);
        if (!url) throw new Error(NO_SOURCE_ERROR);

        const response = await fetch(url, {
          signal: controller.signal,
          credentials: isSameOriginUrl(url) ? "include" : "omit",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const buffer = await response.arrayBuffer();

        if (!isMounted || controller.signal.aborted) return;
        if (loadIdRef.current !== loadId) return;
        if (!containerRef.current) return;

        const ViewerCtor = window.XMindEmbedViewer;
        if (!ViewerCtor) {
          throw new Error("XMIND_NOT_READY");
        }

        if (!viewerRef.current) {
          viewerRef.current = new ViewerCtor({
            el: containerRef.current,
            styles: { width: "100%", height: "100%" },
          });
        } else {
          viewerRef.current.setStyles?.({ width: "100%", height: "100%" });
        }

        viewerRef.current.load(buffer);
        viewerRef.current.setFitMap?.();
        console.info("[XMindViewer] loaded");
        setStatus("ready");
      } catch (error) {
        if (!isMounted || controller.signal.aborted) return;
        setStatus("error");
        setErrorMessage(error instanceof Error ? error.message : undefined);
      }
    };

    void load();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [file, resolvedUrl, ensureFreshFile, refreshKey]);

  React.useEffect(() => {
    const container = containerRef.current;
    return () => {
      viewerRef.current = null;
      container?.replaceChildren();
    };
  }, []);

  if (status === "error") {
    const isSourceError = errorMessage === NO_SOURCE_ERROR;
    return (
      <div className={VIEW_CLASSNAME}>
        <StatusLayout
          icon={File}
          title={
            isSourceError
              ? t("artifacts.viewer.notSupported")
              : t("artifacts.viewer.fetchError")
          }
          desc={isSourceError ? file.name : errorMessage}
          action={
            !isSourceError && (
              <Button
                variant="outline"
                size="sm"
                className="mt-4"
                onClick={() => {
                  setRefreshKey((key) => key + 1);
                }}
              >
                {t("artifacts.viewer.retry")}
              </Button>
            )
          }
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        VIEW_CLASSNAME,
        "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
      )}
    >
      <DocumentViewerToolbar
        file={file}
        subtitle="XMIND"
        resolvedUrl={resolvedUrl}
        onClose={onClose}
        onDownload={handleDownload}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
      <div className="relative flex-1 min-h-0 overflow-hidden">
        <div ref={containerRef} className="h-full w-full bg-background" />
        {status === "loading" && (
          <DocumentViewerOverlaySkeleton
            label={t("artifacts.viewer.loadingDoc")}
          />
        )}
      </div>
    </div>
  );
};

interface DocumentViewerProps {
  file?: FileNode;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
  onClose?: () => void;
  onOpenPreviewWindow?: () => void;
}

const DocumentViewerComponent = ({
  file,
  ensureFreshFile,
  onClose,
  onOpenPreviewWindow,
}: DocumentViewerProps) => {
  const { t } = useT("translation");

  if (!file)
    return (
      <div className="h-full flex flex-col items-center justify-center rounded-xl bg-muted/5 p-12 text-center text-muted-foreground">
        <File className="size-10 mb-4 opacity-20" />
        <p className="text-sm font-medium">
          {t("artifacts.viewer.selectFile")}
        </p>
        <p className="text-xs mt-1 opacity-50">
          {t("artifacts.viewer.supportedFormats")}
        </p>
      </div>
    );

  if (!file.url)
    return (
      <StatusLayout
        icon={File}
        title={t("artifacts.viewer.processing")}
        desc={file.name}
      />
    );

  const resolvedUrl = ensureAbsoluteUrl(file.url);
  const extension = extractExtension(file);
  const docType = DOC_VIEWER_TYPE_MAP[extension];
  const textLanguage = getTextLanguage(extension, file.mimeType);
  const excalidrawFile = isExcalidrawFile(extension, file.mimeType);
  const drawioFile = isDrawioFile(extension, file.mimeType);

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    await downloadFileFromUrl({
      url: refreshed?.url ?? resolvedUrl,
      filename: refreshed?.name || refreshed?.path || "document",
    });
  };

  if (extension === "html" || extension === "htm") {
    return (
      <div
        className={cn(
          VIEW_CLASSNAME,
          "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
        )}
      >
        <DocumentViewerToolbar
          file={file}
          subtitle="HTML PREVIEW"
          resolvedUrl={resolvedUrl}
          onClose={onClose}
          onDownload={handleDownload}
          onOpenPreviewWindow={onOpenPreviewWindow}
        />
        <iframe
          src={resolvedUrl}
          className="h-full w-full border-0 bg-white"
          title={file.name}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        />
      </div>
    );
  }

  if (extension === "xmind") {
    return (
      <XMindDocumentViewer
        file={file}
        resolvedUrl={resolvedUrl}
        ensureFreshFile={ensureFreshFile}
        onClose={onClose}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
    );
  }

  if (excalidrawFile) {
    return (
      <ExcalidrawDocumentViewer
        file={file}
        resolvedUrl={resolvedUrl}
        ensureFreshFile={ensureFreshFile}
        onClose={onClose}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
    );
  }

  if (drawioFile) {
    return (
      <DrawioDocumentViewer
        file={file}
        resolvedUrl={resolvedUrl}
        ensureFreshFile={ensureFreshFile}
        onClose={onClose}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
    );
  }

  if (docType) {
    const subtitle = (extension || docType).toUpperCase();
    const documentUri = resolvedUrl || file.url!;
    return (
      <div
        className={cn(
          VIEW_CLASSNAME,
          "flex min-w-0 flex-col rounded-xl border bg-card shadow-sm",
        )}
      >
        <DocumentViewerToolbar
          file={file}
          subtitle={subtitle}
          resolvedUrl={documentUri}
          onClose={onClose}
          onDownload={handleDownload}
          onOpenPreviewWindow={onOpenPreviewWindow}
        />
        <div className="flex-1 overflow-hidden bg-black/5">
          <DocViewer
            key={documentUri}
            documents={[{ uri: documentUri, fileType: docType }]}
            config={{ header: { disableHeader: true } }}
            className="h-full"
          />
        </div>
      </div>
    );
  }

  if (textLanguage === "markdown") {
    return (
      <MarkdownDocumentViewer
        file={file}
        resolvedUrl={resolvedUrl}
        ensureFreshFile={ensureFreshFile}
        onClose={onClose}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
    );
  }

  if (textLanguage) {
    return (
      <TextDocumentViewer
        file={file}
        language={textLanguage}
        resolvedUrl={resolvedUrl}
        ensureFreshFile={ensureFreshFile}
        onClose={onClose}
        onOpenPreviewWindow={onOpenPreviewWindow}
      />
    );
  }

  return (
    <StatusLayout
      icon={File}
      title={t("artifacts.viewer.notSupported")}
      desc={file.name}
      action={
        resolvedUrl && (
          <div className="flex gap-2 mt-6">
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => {
                const open = async () => {
                  const refreshed = ensureFreshFile
                    ? await ensureFreshFile(file)
                    : file;
                  const url = ensureAbsoluteUrl(refreshed?.url ?? resolvedUrl);
                  if (!url) return;
                  window.open(url, "_blank", "noopener,noreferrer");
                };
                void open();
              }}
            >
              <ExternalLink className="size-4" />
              {t("artifacts.viewer.openInNewWindow")}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={() => {
                void handleDownload();
              }}
            >
              <Download className="size-4" />
              {t("artifacts.viewer.downloadOriginal")}
            </Button>
          </div>
        )
      }
    />
  );
};

export const DocumentViewer = React.memo(DocumentViewerComponent);
DocumentViewer.displayName = "DocumentViewer";

interface StatusLayoutProps {
  icon: React.ElementType;
  title: string;
  desc?: string;
  action?: React.ReactNode;
}

const StatusLayout = ({
  icon: Icon,
  title,
  desc,
  action,
}: StatusLayoutProps) => (
  <div className="flex flex-col items-center justify-center h-full p-8 text-center max-w-sm mx-auto">
    <div className="p-4 bg-muted rounded-full mb-4 opacity-50">
      <Icon className="size-10 text-muted-foreground" />
    </div>
    <h3 className="font-semibold text-base">{title}</h3>
    {desc && (
      <p className="text-xs text-muted-foreground mt-2 leading-relaxed break-words break-all">
        {desc}
      </p>
    )}
    {action}
  </div>
);
