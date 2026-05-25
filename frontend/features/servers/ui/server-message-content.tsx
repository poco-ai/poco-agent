"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkBreaks from "remark-breaks";
import rehypeKatex from "rehype-katex";

import { AdaptiveMarkdown } from "@/components/shared/adaptive-markdown";
import { MarkdownCode, MarkdownPre } from "@/components/shared/markdown-code";
import type {
  ChannelMessageEntity,
  ChannelMessageEntityAction,
  ChannelMessageEntityKind,
} from "@/features/servers/model/types";
import { getFileIcon } from "@/lib/utils/file/get-file-icon";
import { cn } from "@/lib/utils";

type LinkProps = {
  children?: React.ReactNode;
  href?: string;
  ref?: React.Ref<HTMLAnchorElement>;
};

const MENTION_PATTERN = /(@[^\s@,.!?;:]+)/gu;
const ENTITY_KINDS = new Set<ChannelMessageEntityKind>([
  "agent",
  "user",
  "artifact",
  "task",
  "message",
  "thread",
]);
const ENTITY_ACTIONS = new Set<ChannelMessageEntityAction>([
  "trigger",
  "mention",
  "reference",
]);

const ImgBlock = ({
  src,
  alt,
  ...props
}: React.DetailedHTMLProps<
  React.ImgHTMLAttributes<HTMLImageElement>,
  HTMLImageElement
>) => {
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} {...props} />;
};

function renderMentions(text: string): React.ReactNode[] {
  const tokens = text.split(MENTION_PATTERN);
  return tokens.map((token, index) => {
    if (MENTION_PATTERN.test(token)) {
      MENTION_PATTERN.lastIndex = 0;
      return (
        <span
          key={`${token}-${index}`}
          className="cursor-text select-text rounded-md border border-border bg-primary/10 px-1.5 py-0.5 text-sm font-semibold text-foreground"
        >
          {token}
        </span>
      );
    }
    MENTION_PATTERN.lastIndex = 0;
    return <React.Fragment key={`${token}-${index}`}>{token}</React.Fragment>;
  });
}

function renderMentionNodes(node: React.ReactNode): React.ReactNode {
  if (typeof node === "string") {
    return renderMentions(node);
  }

  if (Array.isArray(node)) {
    return node.map((child, index) => (
      <React.Fragment key={index}>{renderMentionNodes(child)}</React.Fragment>
    ));
  }

  if (!React.isValidElement(node)) {
    return node;
  }

  const element = node as React.ReactElement<{ children?: React.ReactNode }>;
  const children = React.Children.map(element.props.children, (child) =>
    renderMentionNodes(child),
  );

  return React.cloneElement(element, undefined, children);
}

function withMentionHighlight<T extends { children?: React.ReactNode }>(
  render: (props: T) => React.ReactElement,
) {
  return (props: T) =>
    render({
      ...props,
      children: React.Children.map(props.children, (child) =>
        renderMentionNodes(child),
      ),
    });
}

function readEntityTextField(
  value: Record<string, unknown>,
  snakeKey: string,
  camelKey: string,
): string | null {
  const raw = value[snakeKey] ?? value[camelKey];
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

function parseMessageEntities(
  messageContent?: Record<string, unknown> | null,
): ChannelMessageEntity[] {
  const rawEntities = messageContent?.entities;
  if (!Array.isArray(rawEntities)) {
    return [];
  }
  return rawEntities.flatMap((rawEntity) => {
    if (!rawEntity || typeof rawEntity !== "object") {
      return [];
    }
    const value = rawEntity as Record<string, unknown>;
    const kind = value.kind;
    const action = value.action;
    const targetId = readEntityTextField(value, "target_id", "targetId");
    const displayText = readEntityTextField(
      value,
      "display_text",
      "displayText",
    );
    const insertedText = readEntityTextField(
      value,
      "inserted_text",
      "insertedText",
    );
    if (
      typeof kind !== "string" ||
      typeof action !== "string" ||
      !ENTITY_KINDS.has(kind as ChannelMessageEntityKind) ||
      !ENTITY_ACTIONS.has(action as ChannelMessageEntityAction) ||
      !targetId ||
      !displayText ||
      !insertedText
    ) {
      return [];
    }
    const rangeValue = value.range;
    const range =
      rangeValue && typeof rangeValue === "object"
        ? (rangeValue as Record<string, unknown>)
        : null;
    const start = typeof range?.start === "number" ? range.start : undefined;
    const end = typeof range?.end === "number" ? range.end : undefined;
    return [
      {
        id: readEntityTextField(value, "id", "id") ?? `${kind}-${targetId}`,
        kind: kind as ChannelMessageEntityKind,
        action: action as ChannelMessageEntityAction,
        targetId,
        displayText,
        insertedText,
        range:
          start !== undefined && end !== undefined ? { start, end } : undefined,
        metadata:
          value.metadata && typeof value.metadata === "object"
            ? (value.metadata as Record<string, unknown>)
            : undefined,
      },
    ];
  });
}

function getEntityChipClassName(entity: ChannelMessageEntity): string {
  if (entity.kind === "agent" || entity.kind === "user") {
    return "border-emerald-500/30 bg-emerald-500/10 text-foreground";
  }
  if (entity.kind === "artifact") {
    return "border-amber-900/30 bg-amber-900/10 text-foreground";
  }
  if (entity.kind === "task") {
    return "border-amber-500/30 bg-amber-500/10 text-foreground";
  }
  return "border-border bg-muted text-foreground";
}

function entityTitle(entity: ChannelMessageEntity): string {
  const target = entity.metadata?.logical_path ?? entity.metadata?.title;
  return typeof target === "string" && target.trim()
    ? target
    : entity.displayText;
}

function getArtifactIconName(entity: ChannelMessageEntity): string {
  const displayName = entity.metadata?.display_name;
  if (typeof displayName === "string" && displayName.trim()) {
    return displayName;
  }
  const logicalPath = entity.metadata?.logical_path;
  if (typeof logicalPath === "string" && logicalPath.trim()) {
    return logicalPath;
  }
  return entity.displayText || entity.insertedText;
}

function getEntityLabel(entity: ChannelMessageEntity): string {
  if (entity.kind === "artifact") {
    return entity.insertedText.replace(/^#/, "");
  }
  return entity.insertedText;
}

function renderEntityText(
  text: string,
  entities: ChannelMessageEntity[],
): React.ReactNode[] {
  const positioned = entities
    .map((entity) => {
      const rangeStart =
        entity.range &&
        text.slice(entity.range.start, entity.range.end) === entity.insertedText
          ? entity.range.start
          : text.indexOf(entity.insertedText);
      return { entity, start: rangeStart };
    })
    .filter((item) => item.start >= 0)
    .sort((left, right) => left.start - right.start);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (const item of positioned) {
    if (item.start < cursor) {
      continue;
    }
    if (item.start > cursor) {
      nodes.push(
        <React.Fragment key={`text-${cursor}`}>
          {text.slice(cursor, item.start)}
        </React.Fragment>,
      );
    }
    const end = item.start + item.entity.insertedText.length;
    const ArtifactIcon =
      item.entity.kind === "artifact"
        ? getFileIcon(getArtifactIconName(item.entity))
        : null;
    nodes.push(
      <span
        key={`${item.entity.id}-${item.start}`}
        title={entityTitle(item.entity)}
        className={cn(
          "inline-flex max-w-full cursor-text select-text items-center rounded-md border px-1.5 py-0.5 text-sm font-semibold align-baseline",
          getEntityChipClassName(item.entity),
        )}
      >
        {ArtifactIcon ? (
          <ArtifactIcon className="mr-1 size-3.5 shrink-0" aria-hidden="true" />
        ) : null}
        {getEntityLabel(item.entity)}
      </span>,
    );
    cursor = end;
  }
  if (cursor < text.length) {
    nodes.push(
      <React.Fragment key={`text-${cursor}`}>
        {text.slice(cursor)}
      </React.Fragment>,
    );
  }
  return nodes;
}

const markdownComponents = {
  pre: MarkdownPre,
  code: MarkdownCode,
  a: ({ children, href, ...props }: LinkProps) => (
    <a
      className="text-foreground underline underline-offset-4 decoration-muted-foreground/30 hover:decoration-foreground transition-colors"
      target="_blank"
      rel="noopener noreferrer"
      href={href}
      {...props}
    >
      {children}
    </a>
  ),
  h1: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h1 className="text-xl font-bold mb-4 mt-6 text-foreground">{children}</h1>
  )),
  h2: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h2 className="text-lg font-bold mb-3 mt-5 text-foreground">{children}</h2>
  )),
  h3: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <h3 className="text-base font-bold mb-2 mt-4 text-foreground">
      {children}
    </h3>
  )),
  p: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <p>{children}</p>
  )),
  li: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <li>{children}</li>
  )),
  blockquote: withMentionHighlight(
    ({ children }: { children?: React.ReactNode }) => (
      <blockquote>{children}</blockquote>
    ),
  ),
  strong: withMentionHighlight(
    ({ children }: { children?: React.ReactNode }) => (
      <strong>{children}</strong>
    ),
  ),
  em: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <em>{children}</em>
  )),
  hr: () => <hr className="my-4 border-border" />,
  img: ImgBlock,
  table: ({ children }: { children?: React.ReactNode }) => (
    <div className="overflow-x-auto my-4 rounded-lg border border-border">
      <table className="w-full table-fixed border-collapse text-sm">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }: { children?: React.ReactNode }) => (
    <thead className="bg-muted/50">{children}</thead>
  ),
  tbody: ({ children }: { children?: React.ReactNode }) => (
    <tbody className="divide-y divide-border">{children}</tbody>
  ),
  th: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <th className="border-b border-border px-4 py-3 text-left font-semibold text-foreground break-words">
      {children}
    </th>
  )),
  td: withMentionHighlight(({ children }: { children?: React.ReactNode }) => (
    <td className="border-b border-border px-4 py-3 text-foreground break-words">
      {children}
    </td>
  )),
};

export function ServerMessageContent({
  content,
  messageContent,
}: {
  content: string;
  messageContent?: Record<string, unknown> | null;
}) {
  const entities = parseMessageEntities(messageContent);
  if (entities.length > 0) {
    return (
      <div className="whitespace-pre-wrap break-words text-base leading-7">
        {renderEntityText(content, entities)}
      </div>
    );
  }

  return (
    <AdaptiveMarkdown className="prose prose-base dark:prose-invert w-full min-w-0 max-w-none overflow-hidden break-words break-all [&_pre]:whitespace-pre-wrap [&_pre]:break-words [&_code]:break-words [&_p]:break-words [&_p]:break-all [&_*]:break-words [&_*]:break-all">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </AdaptiveMarkdown>
  );
}
