"use client";

import * as React from "react";
import { ArrowLeft, Files } from "lucide-react";

import { Button } from "@/components/ui/button";
import { DocumentViewer } from "@/features/chat/components/execution/file-panel/document-viewer";
import {
  FileSidebar,
  downloadFileFromUrl,
} from "@/features/chat/components/execution/file-panel/file-sidebar";
import type { FileNode } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

const overlayDrawerClassName =
  "absolute inset-y-0 right-0 z-30 flex w-full flex-col border-l border-border bg-card md:left-[17rem] md:w-auto lg:left-[18rem] xl:static xl:h-full xl:w-full xl:min-w-0 xl:shrink-0";

function findFirstFile(nodes: FileNode[]): FileNode | null {
  for (const node of nodes) {
    if (node.type === "file") {
      return node;
    }
    if (node.children?.length) {
      const child = findFirstFile(node.children);
      if (child) {
        return child;
      }
    }
  }
  return null;
}

export function SharedArtifactsDrawer({
  files,
  isLoading,
  onClose,
  fileListLayoutClassName = "xl:grid-cols-[minmax(0,1fr)_minmax(12rem,14rem)]",
}: {
  files: FileNode[];
  isLoading: boolean;
  onClose: () => void;
  fileListLayoutClassName?: string;
}) {
  const { t } = useT("translation");
  const [selectedFile, setSelectedFile] = React.useState<
    FileNode | undefined
  >();

  React.useEffect(() => {
    const nextFile = findFirstFile(files) ?? undefined;
    setSelectedFile((current) => {
      if (!current) {
        return nextFile;
      }
      const stillExists = (() => {
        const visit = (nodes: FileNode[]): boolean => {
          for (const node of nodes) {
            if (node.id === current.id) {
              return true;
            }
            if (node.children?.length && visit(node.children)) {
              return true;
            }
          }
          return false;
        };
        return visit(files);
      })();
      return stillExists ? current : nextFile;
    });
  }, [files]);

  const handleDownloadNode = React.useCallback(async (node: FileNode) => {
    if (node.type !== "file" || !node.url) {
      return;
    }
    await downloadFileFromUrl(node.url, node.name);
  }, []);

  return (
    <aside className={overlayDrawerClassName}>
      <div className="flex items-center justify-between gap-3 border-b border-border px-6 py-5">
        <div className="flex min-w-0 items-center gap-3">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            onClick={onClose}
            aria-label={t("conversationView.backToContext")}
            className="shrink-0 xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </Button>
          <div className="min-w-0">
            <p className="text-xl font-semibold text-foreground">
              {t("conversationView.sharedArtifacts.title")}
            </p>
          </div>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("conversationView.close")}
        </Button>
      </div>

      <div
        className={`grid min-h-0 flex-1 grid-cols-1 ${fileListLayoutClassName}`}
      >
        <div className="min-h-0 border-b border-border xl:border-b-0 xl:border-r">
          <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background">
            <div className="min-h-0 flex-1 overflow-hidden">
              {isLoading ? (
                <div className="flex h-full items-center justify-center px-6 text-sm text-muted-foreground">
                  {t("conversationView.loading")}
                </div>
              ) : selectedFile ? (
                <DocumentViewer file={selectedFile} />
              ) : (
                <div className="flex h-full items-center justify-center px-6 text-center">
                  <div className="space-y-3">
                    <Files className="mx-auto size-8 text-muted-foreground/40" />
                    <p className="text-sm text-muted-foreground">
                      {t("conversationView.sharedArtifacts.empty")}
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="min-h-0 overflow-hidden bg-muted/30">
          <FileSidebar
            files={files}
            onFileSelect={setSelectedFile}
            selectedFile={selectedFile}
            embedded
            onDownloadNode={(node) => void handleDownloadNode(node)}
          />
        </div>
      </div>
    </aside>
  );
}
