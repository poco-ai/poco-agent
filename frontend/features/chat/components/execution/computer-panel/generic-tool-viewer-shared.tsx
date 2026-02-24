"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import { SkeletonCircle, SkeletonItem } from "@/components/ui/skeleton-shimmer";
import { SyntaxHighlighter } from "@/lib/markdown/prism";
import type { ToolExecutionResponse } from "@/features/chat/types";
import { CODE_THEME } from "./generic-tool-viewer-utils";

export function FieldRow({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex items-start gap-2 text-xs">
      <span className="text-muted-foreground shrink-0">{label}:</span>
      <span className="break-all [overflow-wrap:anywhere]">
        {String(value)}
      </span>
    </div>
  );
}

export function ToolOutputSkeleton({ label }: { label: string }) {
  return (
    <SkeletonItem className="h-20 min-h-0 w-full">
      <span className="sr-only">{label}</span>
    </SkeletonItem>
  );
}

export function ToolHeader({
  execution,
  title,
  sectionLabel,
}: {
  execution: ToolExecutionResponse;
  title: string;
  sectionLabel: string;
}) {
  const isDone = Boolean(execution.tool_output);
  const isError = execution.is_error;

  return (
    <div className="flex items-center gap-2">
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
        {sectionLabel}
      </span>
      <span className="truncate text-xs font-medium text-foreground">
        {title}
      </span>
      <span className="ml-auto shrink-0">
        {!isDone ? (
          <SkeletonCircle className="size-3.5" />
        ) : isError ? (
          <XCircle className="size-3.5 text-destructive" />
        ) : (
          <CheckCircle2 className="size-3.5 text-primary" />
        )}
      </span>
    </div>
  );
}

export function ContentCodeBlock({
  content,
  language = "text",
}: {
  content: string;
  language?: string;
}) {
  return (
    <SyntaxHighlighter
      language={language}
      style={CODE_THEME}
      wrapLongLines
      customStyle={{
        margin: 0,
        padding: "0.75rem",
        background: "transparent",
        fontSize: "0.75rem",
        lineHeight: "1.5",
      }}
      codeTagProps={{
        style: {
          background: "transparent",
          fontFamily: "inherit",
        },
      }}
    >
      {content}
    </SyntaxHighlighter>
  );
}
