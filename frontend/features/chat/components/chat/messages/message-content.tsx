"use client";

import * as React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import type { MessageBlock } from "@/features/chat/types";
import type { ToolUseBlock, ToolResultBlock } from "@/features/chat/types";
import { ToolChain } from "./tool-chain";
import remarkBreaks from "remark-breaks";
import rehypeKatex from "rehype-katex";
import { MarkdownCode, MarkdownPre } from "@/components/shared/markdown-code";
import { AdaptiveMarkdown } from "@/components/shared/adaptive-markdown";

type LinkProps = {
  children?: React.ReactNode;
  href?: string;
  ref?: React.Ref<HTMLAnchorElement>;
};

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

export function MessageContent({
  content,
  sessionStatus,
}: {
  content: string | MessageBlock[];
  sessionStatus?: string;
}) {
  // Helper function to extract text content from message
  const getTextContent = (content: string | MessageBlock[]): string => {
    const clean = (text: string) => text.replace(/\uFFFD/g, "");

    if (typeof content === "string") {
      return clean(content);
    }
    // If it's an array of blocks, extract text from TextBlock
    if (Array.isArray(content)) {
      // This helper is used for copy-paste mainly, so we just want the text parts
      const textBlocks = content.filter(
        (block: MessageBlock) => block._type === "TextBlock",
      );
      return textBlocks
        .map((block: MessageBlock) =>
          block._type === "TextBlock" ? clean(block.text) : "",
        )
        .join("\n\n");
    }
    return clean(String(content));
  };

  const textContent = getTextContent(content);

  // If content is string, render as before
  if (typeof content === "string") {
    return (
      <AdaptiveMarkdown className="prose prose-base dark:prose-invert w-full min-w-0 max-w-none overflow-hidden break-words break-all [&_pre]:whitespace-pre-wrap [&_pre]:break-words [&_code]:break-words [&_p]:break-words [&_p]:break-all [&_*]:break-words [&_*]:break-all">
        <ReactMarkdown
          remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
          rehypePlugins={[rehypeKatex]}
          components={{
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
            h1: ({ children }) => (
              <h1 className="text-xl font-bold mb-4 mt-6 text-foreground">
                {children}
              </h1>
            ),
            h2: ({ children }) => (
              <h2 className="text-lg font-bold mb-3 mt-5 text-foreground">
                {children}
              </h2>
            ),
            h3: ({ children }) => (
              <h3 className="text-base font-bold mb-2 mt-4 text-foreground">
                {children}
              </h3>
            ),
            hr: () => <hr className="my-4 border-border" />,
            img: ImgBlock,
            table: ({ children }) => (
              <div className="overflow-x-auto my-4 rounded-lg border border-border">
                <table className="w-full table-fixed border-collapse text-sm">
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
              <th className="border-b border-border px-4 py-3 text-left font-semibold text-foreground break-words">
                {children}
              </th>
            ),
            td: ({ children }) => (
              <td className="border-b border-border px-4 py-3 text-foreground break-words">
                {children}
              </td>
            ),
          }}
        >
          {textContent}
        </ReactMarkdown>
      </AdaptiveMarkdown>
    );
  }

  // Handle array of blocks (Tools + Text)
  // We need to group them: sequence of tool/subagent blocks -> dedicated chain, sequence of text blocks -> Markdown
  const toolUseTypeById = new Map<string, "tool" | "subagent">();
  for (const block of content) {
    if (block._type === "ToolUseBlock") {
      toolUseTypeById.set(
        block.id,
        block.name === "Task" ? "subagent" : "tool",
      );
    }
  }

  const groups: {
    type: "text" | "tool" | "subagent" | "thinking";
    blocks: MessageBlock[];
  }[] = [];
  let currentGroup: {
    type: "text" | "tool" | "subagent" | "thinking";
    blocks: MessageBlock[];
  } | null = null;

  for (const block of content) {
    let type: "text" | "tool" | "subagent" | "thinking";
    if (block._type === "ToolUseBlock") {
      type = block.name === "Task" ? "subagent" : "tool";
    } else if (block._type === "ToolResultBlock") {
      type = toolUseTypeById.get(block.tool_use_id) ?? "tool";
    } else if (block._type === "ThinkingBlock") {
      type = "thinking";
    } else {
      type = "text";
    }

    if (!currentGroup || currentGroup.type !== type) {
      currentGroup = { type, blocks: [] };
      groups.push(currentGroup);
    }
    currentGroup.blocks.push(block);
  }

  return (
    <div className="w-full min-w-0 space-y-4 overflow-hidden">
      {groups.map((group, index) => {
        if (group.type === "tool" || group.type === "subagent") {
          return (
            <ToolChain
              key={index}
              blocks={group.blocks as (ToolUseBlock | ToolResultBlock)[]}
              sessionStatus={sessionStatus}
            />
          );
        } else if (group.type === "thinking") {
          const thinking = group.blocks
            .map((b) => (b._type === "ThinkingBlock" ? b.thinking : ""))
            .join("\n\n")
            .trim();

          if (!thinking) return null;

          return (
            <div
              key={index}
              className="my-2 w-full min-w-0 max-w-full overflow-hidden pl-5"
            >
              <pre className="whitespace-pre-wrap break-words [overflow-wrap:anywhere] font-mono text-[11px] text-muted-foreground/90">
                {thinking}
              </pre>
            </div>
          );
        } else {
          const text = group.blocks
            .map((b) => (b._type === "TextBlock" ? b.text : ""))
            .join("\n\n");
          if (!text.trim()) return null;

          return (
            <AdaptiveMarkdown
              key={index}
              className="prose prose-base dark:prose-invert w-full min-w-0 max-w-none overflow-hidden break-words break-all [&_pre]:whitespace-pre-wrap [&_pre]:break-words [&_code]:break-words [&_p]:break-words [&_p]:break-all [&_*]:break-words [&_*]:break-all"
            >
              <ReactMarkdown
                remarkPlugins={[remarkGfm, remarkBreaks, remarkMath]}
                rehypePlugins={[rehypeKatex]}
                components={{
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
                  h1: ({ children }) => (
                    <h1 className="text-xl font-bold mb-4 mt-6 text-foreground">
                      {children}
                    </h1>
                  ),
                  h2: ({ children }) => (
                    <h2 className="text-lg font-bold mb-3 mt-5 text-foreground">
                      {children}
                    </h2>
                  ),
                  h3: ({ children }) => (
                    <h3 className="text-base font-bold mb-2 mt-4 text-foreground">
                      {children}
                    </h3>
                  ),
                  hr: () => <hr className="my-4 border-border" />,
                  img: ImgBlock,
                  table: ({ children }) => (
                    <div className="overflow-x-auto my-4 rounded-lg border border-border">
                      <table className="w-full table-fixed border-collapse text-sm">
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
                    <th className="border-b border-border px-4 py-3 text-left font-semibold text-foreground break-words">
                      {children}
                    </th>
                  ),
                  td: ({ children }) => (
                    <td className="border-b border-border px-4 py-3 text-foreground break-words">
                      {children}
                    </td>
                  ),
                }}
              >
                {text}
              </ReactMarkdown>
            </AdaptiveMarkdown>
          );
        }
      })}
    </div>
  );
}
