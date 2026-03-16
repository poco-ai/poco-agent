"use client";

import * as React from "react";
import {
  ArrowUpRight,
  Download,
  Github,
  Search,
  Sparkles,
  Star,
} from "lucide-react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { Button } from "@/components/ui/button";
import { StaggeredList } from "@/components/ui/staggered-entrance";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type {
  SkillsMpRecommendationSection,
  SkillsMpSkillItem,
} from "@/features/capabilities/skills/types";
import { useT } from "@/lib/i18n/client";

interface SkillMarketplaceBrowserProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  isSemanticSearch: boolean;
  onSemanticSearchChange: (value: boolean) => void;
  onSearch: () => void;
  onReset: () => void;
  isLoading: boolean;
  errorMessage: string | null;
  sections: SkillsMpRecommendationSection[];
  items: SkillsMpSkillItem[];
  hasActiveSearch: boolean;
  onDownload: (item: SkillsMpSkillItem) => void;
  downloadingExternalId?: string | null;
}

function formatUpdatedAt(value: string | null, locale: string): string | null {
  if (!value) return null;

  const trimmed = value.trim();
  const numericValue = Number(trimmed);
  const date = Number.isFinite(numericValue)
    ? new Date(numericValue > 1_000_000_000_000 ? numericValue : numericValue * 1000)
    : new Date(trimmed);
  if (Number.isNaN(date.getTime())) return null;

  try {
    return new Intl.DateTimeFormat(locale, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  } catch {
    return date.toLocaleDateString();
  }
}

function getRepoLabel(url: string | null): string | null {
  if (!url) return null;

  try {
    const parsed = new URL(url);
    if (parsed.hostname !== "github.com") return url;
    const segments = parsed.pathname.split("/").filter(Boolean);
    if (segments.length >= 2) {
      return `${segments[0]}/${segments[1].replace(/\.git$/, "")}`;
    }
    return url;
  } catch {
    return url;
  }
}

function SkillMarketplaceCard({
  item,
  onDownload,
  downloadingExternalId,
}: {
  item: SkillsMpSkillItem;
  onDownload: (item: SkillsMpSkillItem) => void;
  downloadingExternalId?: string | null;
}) {
  const { t, i18n } = useT("translation");
  const updatedAt = formatUpdatedAt(item.updated_at, i18n.language);
  const repoLabel = getRepoLabel(item.github_url);
  const isDownloading = downloadingExternalId === item.external_id;

  return (
    <article className="group overflow-hidden rounded-[1.35rem] border border-border/60 bg-gradient-to-b from-background via-background to-muted/20 shadow-[var(--shadow-sm)] transition-all duration-300 hover:-translate-y-0.5 hover:border-border hover:shadow-[var(--shadow-md)]">
      <div className="space-y-4 px-5 py-5">
        <div className="space-y-2">
          <div className="flex items-start justify-between gap-3">
            <h3
              className="min-w-0 flex-1 truncate text-base font-bold tracking-tight text-foreground"
              style={{
                fontFamily: '"Maple Mono", "Maple Mono NF", var(--font-mono)',
              }}
            >
              {item.name}
            </h3>
            <div className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-xs font-medium text-amber-700 dark:text-amber-300">
              <Star className="size-3.5 fill-current text-amber-500" />
              {item.stars.toLocaleString()}
            </div>
          </div>
        </div>

        <p className="line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-muted-foreground">
          {item.description || t("library.skillsImport.marketplace.noDescription")}
        </p>

        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 text-xs text-muted-foreground">
          {repoLabel && item.github_url ? (
            <a
              href={item.github_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-w-0 items-center gap-1.5 text-foreground/80 transition-colors hover:text-foreground"
            >
              <Github className="size-3.5 shrink-0" />
              <span className="truncate">{repoLabel}</span>
              <ArrowUpRight className="size-3 shrink-0 text-muted-foreground" />
            </a>
          ) : (
            <span />
          )}
          {updatedAt ? (
            <div className="shrink-0">
              {t("library.skillsImport.marketplace.updatedAt")} · {updatedAt}
            </div>
          ) : null}
        </div>
      </div>

      <div className="grid grid-cols-2 border-t border-border/60 bg-muted/10">
        <Button
          variant="ghost"
          className="h-11 rounded-none border-r border-border/60"
          onClick={() => onDownload(item)}
          disabled={isDownloading}
        >
          <Download className="size-4" />
          {isDownloading
            ? t("library.skillsImport.marketplace.downloading")
            : t("library.skillsImport.marketplace.download")}
        </Button>
        <Button variant="ghost" className="h-11 rounded-none" asChild>
          <a href={item.skillsmp_url} target="_blank" rel="noreferrer">
            <ArrowUpRight className="size-4" />
            {t("library.skillsImport.marketplace.jump")}
          </a>
        </Button>
      </div>
    </article>
  );
}

export function SkillMarketplaceBrowser({
  searchQuery,
  onSearchQueryChange,
  isSemanticSearch,
  onSemanticSearchChange,
  onSearch,
  onReset,
  isLoading,
  errorMessage,
  sections,
  items,
  hasActiveSearch,
  onDownload,
  downloadingExternalId,
}: SkillMarketplaceBrowserProps) {
  const { t } = useT("translation");

  const showEmptyState = !isLoading && !errorMessage && items.length === 0;

  return (
    <div className="space-y-5">
      <div className="space-y-3 rounded-[1.5rem] border border-border/60 bg-gradient-to-br from-muted/30 via-background to-background px-4 py-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <HeaderSearchInput
            value={searchQuery}
            onChange={onSearchQueryChange}
            placeholder={t("library.skillsImport.placeholders.marketplaceSearch")}
            className="w-full md:w-full"
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                onSearch();
              }
            }}
          />
          <div className="flex items-center gap-2">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  type="button"
                  variant={isSemanticSearch ? "default" : "outline"}
                  size="icon"
                  disabled={isLoading}
                  onClick={() => onSemanticSearchChange(!isSemanticSearch)}
                  aria-label={t(
                    "library.skillsImport.marketplace.aiSearchTooltip",
                  )}
                >
                  <Sparkles className="size-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent sideOffset={6}>
                {t("library.skillsImport.marketplace.aiSearchTooltip")}
              </TooltipContent>
            </Tooltip>
            <Button onClick={onSearch} disabled={isLoading} className="shrink-0">
              <Search className="size-4" />
              {t("library.skillsImport.marketplace.search")}
            </Button>
            {hasActiveSearch ? (
              <Button variant="outline" onClick={onReset} disabled={isLoading}>
                {t("library.skillsImport.marketplace.reset")}
              </Button>
            ) : null}
          </div>
        </div>
        <p className="text-xs leading-5 text-muted-foreground">
          {t("library.skillsImport.hints.marketplace")}
        </p>
      </div>

      {errorMessage ? (
        <div className="rounded-2xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-sm text-destructive">
          {errorMessage}
        </div>
      ) : null}

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="h-64 animate-pulse rounded-[1.35rem] border border-border/60 bg-muted/20"
            />
          ))}
        </div>
      ) : null}

      {!isLoading && hasActiveSearch ? (
        <div className="space-y-4">
          <div className="text-sm text-muted-foreground">
            {t("library.skillsImport.marketplace.searchResults", {
              count: items.length,
            })}
          </div>
          {showEmptyState ? (
            <div className="rounded-[1.35rem] border border-dashed border-border/70 bg-muted/10 px-5 py-10 text-center text-sm text-muted-foreground">
              {t("library.skillsImport.marketplace.emptySearch")}
            </div>
          ) : (
            <StaggeredList
              items={items}
              show
              className="grid gap-3 sm:grid-cols-2 sm:space-y-0"
              itemClassName="h-full"
              keyExtractor={(item) => item.external_id}
              renderItem={(item) => (
                <SkillMarketplaceCard
                  item={item}
                  onDownload={onDownload}
                  downloadingExternalId={downloadingExternalId}
                />
              )}
            />
          )}
        </div>
      ) : null}

      {!isLoading && !hasActiveSearch ? (
        <div className="space-y-5">
          {sections.map((section) => (
            <section key={section.key} className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <div className="space-y-1">
                  <h3 className="text-base font-semibold tracking-tight">
                    {section.title ||
                      t(`library.skillsImport.marketplace.sections.${section.key}`)}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {t("library.skillsImport.marketplace.recommendationHint")}
                  </p>
                </div>
              </div>
              {section.items.length === 0 ? (
                <div className="rounded-[1.35rem] border border-dashed border-border/70 bg-muted/10 px-5 py-10 text-center text-sm text-muted-foreground">
                  {t("library.skillsImport.marketplace.emptyRecommendations")}
                </div>
              ) : (
                <StaggeredList
                  items={section.items}
                  show
                  className="grid gap-3 sm:grid-cols-2 sm:space-y-0"
                  itemClassName="h-full"
                  keyExtractor={(item) => `${section.key}-${item.external_id}`}
                  renderItem={(item) => (
                    <SkillMarketplaceCard
                      item={item}
                      onDownload={onDownload}
                      downloadingExternalId={downloadingExternalId}
                    />
                  )}
                />
              )}
            </section>
          ))}
        </div>
      ) : null}
    </div>
  );
}
