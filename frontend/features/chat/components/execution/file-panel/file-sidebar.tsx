"use client";

import * as React from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Folder,
  FileText,
  FileCode,
  FileImage,
  File as FileIcon,
  ChevronRight,
  ChevronDown,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileNode } from "@/features/chat/types";
import { apiClient, API_ENDPOINTS } from "@/lib/api-client";
import { toast } from "sonner";
import { PanelHeaderAction } from "@/components/shared/panel-header";
import { useT } from "@/lib/i18n/client";
import { useIsMobile } from "@/hooks/use-mobile";

interface FileSidebarProps {
  files: FileNode[];
  onFileSelect: (file: FileNode) => void;
  selectedFile?: FileNode;
  sessionId?: string;
  embedded?: boolean;
}

function FileTreeItem({
  node,
  onSelect,
  selectedId,
  level = 0,
}: {
  node: FileNode;
  onSelect: (file: FileNode) => void;
  selectedId?: string;
  level?: number;
}) {
  const [isExpanded, setIsExpanded] = React.useState(level === 0);
  const isMobile = useIsMobile();

  // Check if this node or any of its children is the selected one
  const containsSelected = React.useMemo(() => {
    if (!selectedId) return false;
    const check = (n: FileNode): boolean => {
      if (n.id === selectedId) return true;
      if (n.children) {
        return n.children.some((child) => check(child));
      }
      return false;
    };
    return check(node);
  }, [node, selectedId]);

  // Auto-expand if selection is found within subtree
  React.useEffect(() => {
    if (containsSelected && node.type === "folder") {
      setIsExpanded(true);
    }
  }, [containsSelected, node.type]);

  const getFileIcon = (name: string, type: string, className?: string) => {
    if (type === "folder") {
      return <Folder className={cn("size-4", className)} />;
    }

    const ext = name.split(".").pop()?.toLowerCase();
    switch (ext) {
      case "md":
      case "txt":
      case "pdf":
      case "docx":
      case "doc":
        return <FileText className={cn("size-4", className)} />;
      case "xlsx":
      case "xls":
      case "csv":
        return <FileText className={cn("size-4", className)} />;
      case "html":
      case "css":
      case "ts":
      case "tsx":
      case "js":
      case "jsx":
      case "json":
      case "excalidraw":
      case "drawio":
      case "py":
        return <FileCode className={cn("size-4", className)} />;
      case "jpg":
      case "jpeg":
      case "png":
      case "gif":
      case "svg":
        return <FileImage className={cn("size-4", className)} />;
      default:
        return <FileIcon className={cn("size-4", className)} />;
    }
  };

  const handleClick = () => {
    if (node.type === "folder") {
      setIsExpanded(!isExpanded);
    } else {
      onSelect(node);
    }
  };
  // Keep indentation inside the row box so nested nodes never exceed sidebar width.
  const paddingStartRem = 0.5 + Math.min(level, 12) * 0.5;
  const iconColorClass =
    selectedId === node.id
      ? "text-sidebar-accent-foreground"
      : "text-sidebar-foreground/70";

  const renderNodeIcon = () => {
    if (node.type !== "folder") {
      return getFileIcon(node.name, node.type, iconColorClass);
    }

    const folderIcon = getFileIcon(node.name, node.type, iconColorClass);
    const chevronIcon = isExpanded ? (
      <ChevronDown className={cn("size-4", iconColorClass)} />
    ) : (
      <ChevronRight className={cn("size-4", iconColorClass)} />
    );

    if (isMobile) {
      return isExpanded ? folderIcon : chevronIcon;
    }

    return (
      <span className="relative inline-flex items-center justify-center">
        <span className="transition-opacity duration-150 group-hover/item:opacity-0">
          {folderIcon}
        </span>
        <span className="absolute inset-0 transition-opacity duration-150 opacity-0 group-hover/item:opacity-100">
          {chevronIcon}
        </span>
      </span>
    );
  };
  const nodeIcon = renderNodeIcon();

  return (
    <div className="w-full min-w-0 max-w-full basis-full overflow-hidden">
      <div
        className={cn(
          "group/item relative box-border flex w-full min-w-0 max-w-full items-center gap-2 overflow-hidden rounded-md py-1.5 transition-colors cursor-pointer",
          selectedId === node.id
            ? "bg-sidebar-accent text-sidebar-accent-foreground"
            : "text-sidebar-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-accent-foreground",
        )}
        style={{
          paddingInlineStart: `${paddingStartRem}rem`,
          paddingInlineEnd: "0.5rem",
        }}
        onClick={handleClick}
      >
        <span className="shrink-0">{nodeIcon}</span>
        <span
          className="block w-0 flex-1 min-w-0 max-w-full truncate text-sm"
          title={node.name}
        >
          {node.name}
        </span>
      </div>
      {node.type === "folder" && isExpanded && node.children && (
        <div className="w-full min-w-0 max-w-full basis-full overflow-hidden">
          {node.children.map((child) => (
            <FileTreeItem
              key={child.id}
              node={child}
              onSelect={onSelect}
              selectedId={selectedId}
              level={level + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function FileSidebar({
  files,
  onFileSelect,
  selectedFile,
  sessionId,
  embedded = false,
}: FileSidebarProps) {
  const { t } = useT("translation");

  const handleDownload = async () => {
    if (!sessionId) return;
    try {
      const response = await apiClient.get<{
        url?: string | null;
        filename?: string | null;
      }>(API_ENDPOINTS.sessionWorkspaceArchive(sessionId));

      if (response.url) {
        const filename = response.filename || `workspace-${sessionId}.zip`;
        const link = document.createElement("a");
        link.href = response.url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        toast.success(t("fileSidebar.downloadStarted"));
      } else {
        toast.error(t("fileSidebar.archiveNotAvailable"));
      }
    } catch (error) {
      console.error("[Artifacts] Failed to download workspace archive", error);
      toast.error(t("fileSidebar.downloadFailed"));
    }
  };

  return (
    <aside
      className={cn(
        "flex h-full w-full min-h-0 min-w-0 max-w-full flex-col overflow-hidden text-sidebar-foreground",
        embedded
          ? "border-0 bg-transparent"
          : "border-l border-border/60 bg-sidebar/60",
      )}
    >
      <div className="flex w-full min-w-0 items-center justify-between overflow-hidden px-3 py-2">
        <span className="min-w-0 truncate text-xs font-semibold uppercase tracking-wide text-sidebar-foreground/70">
          {t("fileSidebar.title")}
        </span>
        {sessionId && (
          <PanelHeaderAction
            onClick={handleDownload}
            aria-label={t("fileSidebar.downloadAll")}
          >
            <Download className="size-4" />
          </PanelHeaderAction>
        )}
      </div>
      <ScrollArea className="h-full w-full flex-1 min-h-0 max-w-full [&_[data-slot=scroll-area-scrollbar]]:hidden [&_[data-slot=scroll-area-viewport]]:w-full [&_[data-slot=scroll-area-viewport]]:overflow-x-hidden [&_[data-slot=scroll-area-viewport]]:scrollbar-hide">
        <div className="w-full min-w-0 max-w-full space-y-1 overflow-hidden px-2 py-2">
          {files.length === 0 ? (
            <p className="text-xs text-sidebar-foreground/60 px-2 py-1">
              {t("fileSidebar.noFiles")}
            </p>
          ) : (
            files.map((file) => (
              <FileTreeItem
                key={file.id}
                node={file}
                onSelect={onFileSelect}
                selectedId={selectedFile?.id}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </aside>
  );
}
