import type { SourceInfo } from "@/features/capabilities/types/source";

type TFunc = (key: string, options?: Record<string, unknown>) => string;

export function formatSourceLabel(
  source: SourceInfo | null | undefined,
  t: TFunc,
): string {
  const kind = source?.kind;

  if (kind === "github") {
    const repo = source?.repo?.trim();
    const ref = source?.ref?.trim();
    const url = source?.url?.trim();
    if (repo && ref) return `${repo}@${ref}`;
    if (repo) return repo;
    if (url) return url;
    if (ref) return `@${ref}`;
    return t("library.sources.unknown");
  }

  if (kind === "zip") {
    const filename = source?.filename?.trim();
    const url = source?.url?.trim();
    if (filename) return filename;
    if (url) return url;
    return t("library.sources.unknown");
  }

  if (kind === "system") return t("library.sources.system");
  if (kind === "skill-creator") return t("library.sources.skillCreator");
  if (kind === "marketplace") {
    const market = source?.market?.trim();
    if (market === "skillsmp") return t("library.sources.skillsmp");
    return t("library.sources.marketplace");
  }
  if (kind === "manual") return t("library.sources.manual");
  return t("library.sources.unknown");
}
