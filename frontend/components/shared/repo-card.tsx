import { Github } from "lucide-react";
import { BaseCard } from "./base-card";

function deriveRepoLabel(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return "";
  try {
    const parsed = new URL(trimmed);
    const parts = parsed.pathname.split("/").filter(Boolean);
    if (parts.length >= 2) {
      const owner = parts[0];
      let repo = parts[1];
      if (repo.endsWith(".git")) repo = repo.slice(0, -4);
      if (owner && repo) return `${owner}/${repo}`;
    }
    return parsed.hostname || trimmed;
  } catch {
    return trimmed;
  }
}

export interface RepoCardProps {
  url: string;
  branch?: string | null;
  className?: string;
  onOpen?: () => void;
  onRemove?: () => void;
  showRemove?: boolean;
}

export function RepoCard({
  url,
  branch,
  className,
  onOpen,
  onRemove,
  showRemove = Boolean(onRemove),
}: RepoCardProps) {
  const trimmedUrl = url.trim();
  const trimmedBranch = (branch || "").trim();
  const label = deriveRepoLabel(trimmedUrl) || trimmedUrl;
  const subtitle = trimmedBranch
    ? `${trimmedUrl} @${trimmedBranch}`
    : trimmedUrl;

  return (
    <BaseCard
      icon={<Github className="size-4" />}
      title={label}
      subtitle={subtitle}
      onClick={onOpen}
      onRemove={onRemove}
      showRemove={showRemove}
      className={className}
    />
  );
}
