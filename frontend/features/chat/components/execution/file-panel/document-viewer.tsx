"use client";

import * as React from "react";
import dynamic from "next/dynamic";
import type { FileNode } from "@/features/chat/types";
import {
  File,
  Download,
  ExternalLink,
  Loader2,
  Check,
  Copy,
  ChevronLeft,
} from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { Button } from "@/components/ui/button";
import type { DocViewerProps } from "react-doc-viewer";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";
import { MarkdownCode, MarkdownPre } from "@/components/shared/markdown-code";
import { SyntaxHighlighter, oneDark, oneLight } from "@/lib/markdown/prism";
import {
  DOC_VIEWER_TYPE_MAP,
  DEFAULT_TEXT_LANGUAGE,
  ensureAbsoluteUrl,
  extractExtension,
  getTextLanguage,
} from "./document-viewer-utils";

const dispatchCloseViewer = () => {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("close-document-viewer"));
};

function DocViewerLoading() {
  const { t } = useT("translation");
  return (
    <div className="h-full flex items-center justify-center p-8 text-muted-foreground animate-pulse text-sm">
      {t("artifacts.viewer.loadingEngine")}
    </div>
  );
}

const DocViewer = dynamic<DocViewerProps>(
  () => import("./doc-viewer-client").then((m) => m.DocViewerClient),
  {
    ssr: false,
    loading: () => <DocViewerLoading />,
  },
);

const VIEW_CLASSNAME =
  "h-full w-full max-h-full animate-in fade-in duration-300 [--tw-enter-opacity:1] [--tw-enter-scale:1] [--tw-enter-translate-x:0] [--tw-enter-translate-y:0] overflow-hidden flex flex-col min-h-0";
const NO_SOURCE_ERROR = "NO_SOURCE";

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

interface ViewerToolbarProps {
  file: FileNode;
  subtitle?: string;
  resolvedUrl?: string;
  onDownload?: () => void | Promise<void>;
  onCopy?: () => void;
  copyDisabled?: boolean;
  copyState?: "idle" | "copied";
}

const DocumentViewerToolbar = ({
  file,
  subtitle,
  resolvedUrl,
  onDownload,
  onCopy,
  copyDisabled,
  copyState = "idle",
}: ViewerToolbarProps) => (
  <div className="w-full border-b px-3 py-2 text-xs text-muted-foreground sm:px-4 overflow-hidden">
    <div className="flex items-center gap-3 min-w-0 overflow-hidden">
      <Button
        size="icon"
        variant="ghost"
        className="h-8 w-8 shrink-0"
        onClick={dispatchCloseViewer}
      >
        <ChevronLeft className="size-4" />
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
            className="h-8 w-8"
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
            className="h-8 w-8"
            onClick={() => {
              if (onDownload) {
                void onDownload();
                return;
              }
              const link = document.createElement("a");
              link.href = resolvedUrl;
              link.download = file.name || file.path || "document";
              link.click();
            }}
          >
            <Download className="size-4" />
          </Button>
        )}
      </div>
    </div>
  </div>
);

interface TextDocumentViewerProps {
  file: FileNode;
  language?: string;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
}

const TextDocumentViewer = ({
  file,
  language = DEFAULT_TEXT_LANGUAGE,
  resolvedUrl,
  ensureFreshFile,
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
    const url = ensureAbsoluteUrl(refreshed?.url ?? resolvedUrl);
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = refreshed?.name || refreshed?.path || "document";
    link.click();
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
    return (
      <div
        className={cn(
          VIEW_CLASSNAME,
          "flex min-w-0 items-center justify-center text-sm text-muted-foreground",
        )}
      >
        <Loader2 className="mr-2 size-4 animate-spin" />
        {t("artifacts.viewer.loadingDoc")}
      </div>
    );
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
        onDownload={handleDownload}
        onCopy={handleCopy}
        copyDisabled={false}
        copyState={copyState}
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
}: {
  file: FileNode;
  resolvedUrl?: string;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
}) => {
  const { t } = useT("translation");
  const { state, refetch } = useFileTextContent({
    file,
    fallbackUrl: resolvedUrl,
  });
  const [copyState, setCopyState] = React.useState<"idle" | "copied">("idle");

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    const url = ensureAbsoluteUrl(refreshed?.url ?? resolvedUrl);
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = refreshed?.name || refreshed?.path || "document";
    link.click();
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
    return (
      <div
        className={cn(
          VIEW_CLASSNAME,
          "flex min-w-0 items-center justify-center text-sm text-muted-foreground",
        )}
      >
        <Loader2 className="mr-2 size-4 animate-spin" />
        {t("artifacts.viewer.loadingDoc")}
      </div>
    );
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
        onDownload={handleDownload}
        onCopy={handleCopy}
        copyDisabled={false}
        copyState={copyState}
      />
      <div className="flex-1 overflow-auto bg-background min-h-0">
        <div className="mx-auto w-full max-w-4xl px-6 py-8">
          <div className="prose prose-sm dark:prose-invert max-w-none break-words [&_*]:break-words">
            <ReactMarkdown
              remarkPlugins={[remarkGfm, remarkBreaks]}
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

interface DocumentViewerProps {
  file?: FileNode;
  ensureFreshFile?: (file: FileNode) => Promise<FileNode | undefined>;
}

const DocumentViewerComponent = ({
  file,
  ensureFreshFile,
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

  const handleDownload = async () => {
    const refreshed = ensureFreshFile ? await ensureFreshFile(file) : file;
    const url = ensureAbsoluteUrl(refreshed?.url ?? resolvedUrl);
    if (!url) return;
    const link = document.createElement("a");
    link.href = url;
    link.download = refreshed?.name || refreshed?.path || "document";
    link.click();
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
          onDownload={handleDownload}
        />
        <iframe
          src={resolvedUrl}
          className="h-full w-full border-0 bg-background"
          title={file.name}
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
        />
      </div>
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
          onDownload={handleDownload}
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
