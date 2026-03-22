"use client";

import {
  Archive,
  BadgeQuestionMark,
  Bot,
  Compass,
  Github,
  Pencil,
  ShieldCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import type {
  SourceInfo,
  SourceKind,
} from "@/features/capabilities/types/source";
import { cn } from "@/lib/utils";

const SOURCE_ICON_MAP: Record<SourceKind, LucideIcon> = {
  github: Github,
  zip: Archive,
  system: ShieldCheck,
  manual: Pencil,
  "skill-creator": Bot,
  marketplace: Compass,
  unknown: BadgeQuestionMark,
};

function getInitial(name: string): string {
  const normalized = name.trim();
  if (!normalized) return "?";
  return Array.from(normalized)[0]?.toUpperCase() ?? "?";
}

interface CapabilitySourceAvatarProps {
  name: string;
  source?: SourceInfo | null;
  status?: "active" | "inactive" | "error";
  className?: string;
  statusDotClassName?: string;
}

const STATUS_DOT_CLASS: Record<
  NonNullable<CapabilitySourceAvatarProps["status"]>,
  string
> = {
  active: "bg-emerald-500",
  inactive: "bg-muted-foreground/40",
  error: "bg-amber-500",
};

function getSafeExternalUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.toString();
    }
    return null;
  } catch {
    return null;
  }
}

export function CapabilitySourceAvatar({
  name,
  source,
  status = "inactive",
  className,
  statusDotClassName,
}: CapabilitySourceAvatarProps) {
  const hasSource = source !== null && source !== undefined;
  const SourceIcon = hasSource
    ? SOURCE_ICON_MAP[source.kind ?? "unknown"]
    : null;
  const initial = getInitial(name);
  const sourceUrl = getSafeExternalUrl(source?.url);
  const avatarClassName = cn(
    "relative flex size-9 shrink-0 items-center justify-center rounded-full border border-border/60 bg-muted/40 text-muted-foreground",
    sourceUrl
      ? "cursor-pointer transition-colors hover:border-primary/50 hover:bg-muted/70"
      : null,
    className,
  );

  const avatarContent = (
    <>
      {SourceIcon ? (
        <SourceIcon className="size-4" />
      ) : (
        <span className="text-sm font-semibold leading-none">{initial}</span>
      )}
      <span
        aria-hidden="true"
        className={cn(
          "absolute -bottom-0.5 -right-0.5 size-2.5 rounded-full border border-background",
          STATUS_DOT_CLASS[status],
          statusDotClassName,
        )}
      />
    </>
  );

  if (sourceUrl) {
    return (
      <a
        href={sourceUrl}
        target="_blank"
        rel="noreferrer noopener"
        className={avatarClassName}
        title={sourceUrl}
        aria-label={`Open source for ${name}`}
      >
        {avatarContent}
      </a>
    );
  }

  return (
    <div aria-hidden="true" className={avatarClassName}>
      {avatarContent}
    </div>
  );
}
