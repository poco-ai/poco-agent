"use client";

import * as React from "react";
import { useTheme } from "next-themes";
import { Check, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  SyntaxHighlighter,
  getPrismLanguage,
  oneDark,
  oneLight,
} from "@/lib/markdown/prism";

type MarkdownCodeProps = React.ComponentPropsWithoutRef<"code"> & {
  node?: unknown;
};

type MarkdownPreProps = React.ComponentPropsWithoutRef<"pre"> & {
  node?: unknown;
};

type MermaidBlockProps = {
  code: string;
  isDark: boolean;
};

const extractLanguage = (className?: string) => {
  if (!className) return undefined;
  const match = className.match(/language-([^\s]+)/);
  return match?.[1];
};

const MermaidBlock = ({ code, isDark }: MermaidBlockProps) => {
  const baseRenderId = React.useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const renderCountRef = React.useRef(0);
  const [svg, setSvg] = React.useState<string | null>(null);
  const [renderFailed, setRenderFailed] = React.useState(false);

  React.useEffect(() => {
    let mounted = true;

    const renderMermaid = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: isDark ? "dark" : "default",
        });

        renderCountRef.current += 1;
        const { svg: nextSvg } = await mermaid.render(
          `mermaid-${baseRenderId}-${renderCountRef.current}`,
          code,
        );

        if (!mounted) {
          return;
        }

        setSvg(nextSvg);
        setRenderFailed(false);
      } catch (error) {
        if (!mounted) {
          return;
        }

        console.error("[MarkdownPre] Mermaid render failed", error);
        setSvg(null);
        setRenderFailed(true);
      }
    };

    void renderMermaid();

    return () => {
      mounted = false;
    };
  }, [baseRenderId, code, isDark]);

  if (renderFailed) {
    return (
      <SyntaxHighlighter
        language="markdown"
        style={isDark ? oneDark : oneLight}
        wrapLongLines
        customStyle={{
          margin: 0,
          padding: "1rem",
          background: "transparent",
          fontSize: "0.85rem",
          lineHeight: "1.6",
        }}
        codeTagProps={{
          style: {
            background: "transparent",
          },
        }}
      >
        {code}
      </SyntaxHighlighter>
    );
  }

  if (!svg) {
    return <div className="min-h-24 w-full animate-pulse bg-muted/40" />;
  }

  return (
    <div
      className="overflow-x-auto px-4 py-4 [&_svg]:mx-auto [&_svg]:h-auto [&_svg]:max-w-full"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

export const MarkdownCode = ({
  node,
  className,
  children,
  ...props
}: MarkdownCodeProps) => {
  void node; // react-markdown passes `node`; don't forward it to the DOM.
  return (
    <code
      className={[
        "px-1.5 py-0.5 rounded bg-muted text-muted-foreground text-[0.85rem]",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      {...props}
    >
      {children}
    </code>
  );
};

export const MarkdownPre = ({ node, children, ...props }: MarkdownPreProps) => {
  void node; // react-markdown passes `node`; don't forward it to the DOM.
  const { resolvedTheme } = useTheme();
  const [copied, setCopied] = React.useState(false);

  // `react-markdown@10` no longer passes an `inline` prop; handle code blocks at the `<pre>` level.
  type CodeChildProps = { children?: React.ReactNode; className?: string };
  const codeChild = React.Children.toArray(children).find(
    (child): child is React.ReactElement<CodeChildProps> =>
      React.isValidElement<CodeChildProps>(child) &&
      typeof child.props.children !== "undefined",
  );

  if (!codeChild) {
    return <pre {...props}>{children}</pre>;
  }

  const rawCode = codeChild?.props?.children;
  const rawCodeText = Array.isArray(rawCode) ? rawCode.join("") : rawCode;
  const code = String(rawCodeText ?? "").replace(/\n$/, "");

  const codeClassName =
    typeof codeChild?.props?.className === "string"
      ? codeChild.props.className
      : undefined;

  const rawLanguage = extractLanguage(codeClassName)?.toLowerCase();
  const isMermaid = rawLanguage === "mermaid";
  const language = getPrismLanguage(rawLanguage);
  const syntaxTheme = resolvedTheme === "dark" ? oneDark : oneLight;

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error("[MarkdownPre] Copy failed", error);
    }
  };

  return (
    <div className="relative group my-4 w-full min-w-0 max-w-full overflow-hidden rounded-xl border bg-muted/40">
      <div className="absolute right-2 top-2 z-10 opacity-0 transition-opacity group-hover:opacity-100">
        <Button
          size="icon"
          variant="ghost"
          className="h-8 w-8"
          onClick={onCopy}
        >
          {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
        </Button>
      </div>
      <div className="max-w-full overflow-hidden bg-background/80">
        {isMermaid ? (
          <MermaidBlock code={code} isDark={resolvedTheme === "dark"} />
        ) : (
          <SyntaxHighlighter
            language={language}
            style={syntaxTheme}
            wrapLongLines
            customStyle={{
              margin: 0,
              padding: "1rem",
              background: "transparent",
              fontSize: "0.85rem",
              lineHeight: "1.6",
            }}
            codeTagProps={{
              style: {
                background: "transparent",
              },
            }}
          >
            {code}
          </SyntaxHighlighter>
        )}
      </div>
    </div>
  );
};
