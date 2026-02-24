"use client";

import * as React from "react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import type { ToolExecutionResponse } from "@/features/chat/types";
import {
  ContentCodeBlock,
  FieldRow,
  ToolHeader,
  ToolOutputSkeleton,
} from "./generic-tool-viewer-shared";
import {
  TOOL_NAME_TRANSLATION_KEY_MAP,
  guessCodeLanguage,
  isRecord,
  normalizeToolName,
  parseToolOutputPayload,
  stringifyForDisplay,
  stripReadLineMarkers,
} from "./generic-tool-viewer-utils";

type GenericToolViewerProps = {
  execution: ToolExecutionResponse;
};

function WriteToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const input = execution.tool_input ?? {};
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const output = isRecord(outputPayload) ? outputPayload : null;
  const filePath =
    (typeof input["file_path"] === "string" && input["file_path"]) ||
    (typeof input["path"] === "string" && input["path"]) ||
    (typeof output?.["file_path"] === "string" &&
      (output["file_path"] as string)) ||
    "";
  const writtenContent =
    typeof input["content"] === "string" ? (input["content"] as string) : "";
  const outputText = stringifyForDisplay(outputPayload);
  const hasOutput = Boolean(execution.tool_output);

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />

      <div className="space-y-1 rounded-md border bg-background p-3">
        <FieldRow
          label={t("chat.toolCards.fields.filePath")}
          value={filePath}
        />
        <FieldRow
          label={t("chat.toolCards.fields.bytes")}
          value={
            typeof output?.["bytes_written"] === "number"
              ? output["bytes_written"]
              : null
          }
        />
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.toolCards.fields.content")}
        </div>
        <div className="w-full min-w-0 max-w-full overflow-hidden rounded-md border bg-background">
          {writtenContent ? (
            <ContentCodeBlock
              content={writtenContent}
              language={guessCodeLanguage(filePath)}
            />
          ) : (
            <div className="p-3 text-xs text-muted-foreground">
              {t("chat.toolCards.text.empty")}
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.output")}
        </div>
        {hasOutput ? (
          <div
            className={cn(
              "w-full min-w-0 max-w-full overflow-hidden rounded-md border p-3",
              execution.is_error
                ? "border-destructive/30 bg-destructive/5"
                : "border-border bg-background",
            )}
          >
            <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word] text-xs">
              {outputText.trim() ? outputText : t("chat.toolCards.text.empty")}
            </pre>
          </div>
        ) : (
          <ToolOutputSkeleton label={t("computer.terminal.running")} />
        )}
      </div>
    </div>
  );
}

function ReadToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const input = execution.tool_input ?? {};
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const output = isRecord(outputPayload) ? outputPayload : null;
  const filePath =
    (typeof input["file_path"] === "string" && input["file_path"]) ||
    (typeof input["path"] === "string" && input["path"]) ||
    "";

  const contentText =
    typeof output?.["content"] === "string" ? output["content"] : null;
  const imageBase64 =
    typeof output?.["image"] === "string" ? output["image"] : null;
  const imageMimeType =
    typeof output?.["mime_type"] === "string"
      ? output["mime_type"]
      : "image/png";
  const hasOutput = Boolean(execution.tool_output);

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />

      <div className="space-y-1 rounded-md border bg-background p-3">
        <FieldRow
          label={t("chat.toolCards.fields.filePath")}
          value={filePath}
        />
        <FieldRow
          label={t("chat.toolCards.fields.totalLines")}
          value={
            typeof output?.["total_lines"] === "number"
              ? output["total_lines"]
              : null
          }
        />
        <FieldRow
          label={t("chat.toolCards.fields.linesReturned")}
          value={
            typeof output?.["lines_returned"] === "number"
              ? output["lines_returned"]
              : null
          }
        />
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.output")}
        </div>
        {!hasOutput ? (
          <ToolOutputSkeleton label={t("computer.terminal.running")} />
        ) : imageBase64 ? (
          <div className="rounded-md border bg-background p-2">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`data:${imageMimeType};base64,${imageBase64}`}
              alt={t("computer.browser.screenshotAlt")}
              className="mx-auto max-h-[340px] w-auto rounded-sm object-contain"
            />
          </div>
        ) : (
          <div
            className={cn(
              "w-full min-w-0 max-w-full overflow-hidden rounded-md border",
              execution.is_error
                ? "border-destructive/30 bg-destructive/5"
                : "border-border bg-background",
            )}
          >
            <ContentCodeBlock
              content={
                (contentText ? stripReadLineMarkers(contentText) : "") ||
                stripReadLineMarkers(
                  stringifyForDisplay(outputPayload).trim(),
                ) ||
                t("chat.toolCards.text.empty")
              }
              language={guessCodeLanguage(filePath)}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function EditToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const input = execution.tool_input ?? {};
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const output = isRecord(outputPayload) ? outputPayload : null;
  const filePath =
    (typeof input["file_path"] === "string" && input["file_path"]) ||
    (typeof input["path"] === "string" && input["path"]) ||
    (typeof output?.["file_path"] === "string" &&
      (output["file_path"] as string)) ||
    "";
  const oldString =
    typeof input["old_string"] === "string"
      ? (input["old_string"] as string)
      : "";
  const newString =
    typeof input["new_string"] === "string"
      ? (input["new_string"] as string)
      : "";
  const hasOutput = Boolean(execution.tool_output);
  const outputText = stringifyForDisplay(outputPayload);

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />

      <div className="space-y-1 rounded-md border bg-background p-3">
        <FieldRow
          label={t("chat.toolCards.fields.filePath")}
          value={filePath}
        />
        <FieldRow
          label={t("chat.toolCards.fields.replaceAll")}
          value={
            typeof input["replace_all"] === "boolean"
              ? input["replace_all"]
              : null
          }
        />
        <FieldRow
          label={t("chat.toolCards.fields.replacements")}
          value={
            typeof output?.["replacements"] === "number"
              ? output["replacements"]
              : null
          }
        />
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.input")}
        </div>
        <div className="grid grid-cols-1 gap-2">
          <div className="overflow-hidden rounded-md border bg-background">
            <div className="border-b px-3 py-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
              {t("chat.toolCards.fields.oldString")}
            </div>
            <ContentCodeBlock
              content={oldString || t("chat.toolCards.text.empty")}
              language={guessCodeLanguage(filePath)}
            />
          </div>
          <div className="overflow-hidden rounded-md border bg-background">
            <div className="border-b px-3 py-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
              {t("chat.toolCards.fields.newString")}
            </div>
            <ContentCodeBlock
              content={newString || t("chat.toolCards.text.empty")}
              language={guessCodeLanguage(filePath)}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.output")}
        </div>
        {hasOutput ? (
          <div
            className={cn(
              "w-full min-w-0 max-w-full overflow-hidden rounded-md border p-3",
              execution.is_error
                ? "border-destructive/30 bg-destructive/5"
                : "border-border bg-background",
            )}
          >
            <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word] text-xs">
              {outputText.trim() ? outputText : t("chat.toolCards.text.empty")}
            </pre>
          </div>
        ) : (
          <ToolOutputSkeleton label={t("computer.terminal.running")} />
        )}
      </div>
    </div>
  );
}

function GlobToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const input = execution.tool_input ?? {};
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const output = isRecord(outputPayload) ? outputPayload : null;
  const matches = Array.isArray(output?.["matches"])
    ? (output?.["matches"] as unknown[]).filter(
        (item): item is string => typeof item === "string",
      )
    : [];

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />

      <div className="space-y-1 rounded-md border bg-background p-3">
        <FieldRow
          label={t("chat.toolCards.fields.pattern")}
          value={typeof input["pattern"] === "string" ? input["pattern"] : null}
        />
        <FieldRow
          label={t("chat.toolCards.fields.path")}
          value={typeof input["path"] === "string" ? input["path"] : null}
        />
        <FieldRow
          label={t("chat.toolCards.fields.total")}
          value={
            typeof output?.["count"] === "number"
              ? output["count"]
              : matches.length
          }
        />
        <FieldRow
          label={t("chat.toolCards.fields.searchPath")}
          value={
            typeof output?.["search_path"] === "string"
              ? output["search_path"]
              : null
          }
        />
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.toolCards.fields.matches")}
        </div>
        <div className="rounded-md border bg-background p-3">
          {matches.length > 0 ? (
            <ul className="space-y-1 text-xs font-mono">
              {matches.map((item) => (
                <li key={item} className="break-all [overflow-wrap:anywhere]">
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <pre className="text-xs whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]">
              {stringifyForDisplay(outputPayload).trim() ||
                t("chat.toolCards.text.empty")}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

function GrepToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const input = execution.tool_input ?? {};
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const output = isRecord(outputPayload) ? outputPayload : null;
  const matchItems = Array.isArray(output?.["matches"])
    ? output?.["matches"]
    : [];
  const fileItems = Array.isArray(output?.["files"]) ? output?.["files"] : [];

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />

      <div className="space-y-1 rounded-md border bg-background p-3">
        <FieldRow
          label={t("chat.toolCards.fields.pattern")}
          value={typeof input["pattern"] === "string" ? input["pattern"] : null}
        />
        <FieldRow
          label={t("chat.toolCards.fields.path")}
          value={typeof input["path"] === "string" ? input["path"] : null}
        />
        <FieldRow
          label={t("chat.toolCards.fields.outputMode")}
          value={
            typeof input["output_mode"] === "string"
              ? input["output_mode"]
              : null
          }
        />
        <FieldRow
          label={t("chat.toolCards.fields.totalMatches")}
          value={
            typeof output?.["total_matches"] === "number"
              ? output["total_matches"]
              : typeof output?.["count"] === "number"
                ? output["count"]
                : null
          }
        />
      </div>

      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.output")}
        </div>
        <div className="rounded-md border bg-background p-3">
          {matchItems.length > 0 ? (
            <ul className="space-y-2 text-xs">
              {matchItems.map((item, index) => {
                if (!isRecord(item)) {
                  return (
                    <li key={`m-${index}`} className="font-mono break-all">
                      {stringifyForDisplay(item)}
                    </li>
                  );
                }
                const file =
                  typeof item["file"] === "string"
                    ? (item["file"] as string)
                    : "";
                const lineNumber =
                  typeof item["line_number"] === "number"
                    ? (item["line_number"] as number)
                    : null;
                const line =
                  typeof item["line"] === "string"
                    ? (item["line"] as string)
                    : "";
                return (
                  <li key={`m-${index}`} className="space-y-1">
                    <div className="font-mono text-muted-foreground break-all">
                      {file}
                      {lineNumber !== null ? `:${lineNumber}` : ""}
                    </div>
                    <div className="font-mono break-all [overflow-wrap:anywhere]">
                      {line || t("chat.toolCards.text.empty")}
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : fileItems.length > 0 ? (
            <ul className="space-y-1 text-xs font-mono">
              {fileItems.map((item, index) => (
                <li
                  key={`f-${index}`}
                  className="break-all [overflow-wrap:anywhere]"
                >
                  {typeof item === "string" ? item : stringifyForDisplay(item)}
                </li>
              ))}
            </ul>
          ) : (
            <pre className="text-xs whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]">
              {stringifyForDisplay(outputPayload).trim() ||
                t("chat.toolCards.text.empty")}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

function DefaultToolViewer({
  execution,
  title,
}: {
  execution: ToolExecutionResponse;
  title: string;
}) {
  const { t } = useT("translation");
  const isDone = Boolean(execution.tool_output);
  const inputText = stringifyForDisplay(execution.tool_input ?? {});
  const outputPayload = React.useMemo(
    () => parseToolOutputPayload(execution),
    [execution],
  );
  const outputText = stringifyForDisplay(outputPayload);

  return (
    <div className="space-y-3">
      <ToolHeader
        execution={execution}
        title={title}
        sectionLabel={t("chat.toolCards.tools.tool")}
      />
      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.input")}
        </div>
        <div className="rounded-md border bg-background p-3">
          <pre className="text-xs whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]">
            {inputText}
          </pre>
        </div>
      </div>
      <div className="space-y-2">
        <div className="text-[11px] uppercase tracking-wide text-muted-foreground">
          {t("chat.output")}
        </div>
        {isDone ? (
          <div
            className={cn(
              "rounded-md border p-3",
              execution.is_error
                ? "border-destructive/30 bg-destructive/5"
                : "border-border bg-background",
            )}
          >
            <pre className="text-xs whitespace-pre-wrap break-words [overflow-wrap:anywhere] [word-break:break-word]">
              {outputText.trim() ? outputText : t("chat.toolCards.text.empty")}
            </pre>
          </div>
        ) : (
          <ToolOutputSkeleton label={t("computer.terminal.running")} />
        )}
      </div>
    </div>
  );
}

export function GenericToolViewer({ execution }: GenericToolViewerProps) {
  const { t } = useT("translation");

  const normalizedToolName = normalizeToolName(execution.tool_name || "");
  const translationKey = TOOL_NAME_TRANSLATION_KEY_MAP[normalizedToolName];
  const title = translationKey
    ? t(`chat.toolCards.tools.${translationKey}`).trim()
    : (execution.tool_name || t("chat.toolCards.tools.tool")).trim();

  const body = (() => {
    switch (normalizedToolName) {
      case "write":
        return <WriteToolViewer execution={execution} title={title} />;
      case "read":
        return <ReadToolViewer execution={execution} title={title} />;
      case "edit":
        return <EditToolViewer execution={execution} title={title} />;
      case "glob":
        return <GlobToolViewer execution={execution} title={title} />;
      case "grep":
        return <GrepToolViewer execution={execution} title={title} />;
      default:
        return <DefaultToolViewer execution={execution} title={title} />;
    }
  })();

  return (
    <div className="h-full w-full bg-card">
      <ScrollArea className="h-full">
        <div className="p-4 font-mono text-xs space-y-3 min-w-0 max-w-full">
          {body}
        </div>
      </ScrollArea>
    </div>
  );
}
