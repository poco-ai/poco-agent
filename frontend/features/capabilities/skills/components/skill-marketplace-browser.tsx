"use client";

import * as React from "react";
import {
  ArrowUpRight,
  Clock3,
  Download,
  Flame,
  Github,
  RefreshCw,
  Search,
  Sparkles,
  Star,
} from "lucide-react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { StaggeredList } from "@/components/ui/staggered-entrance";
import type {
  SkillsMpRecommendationSection,
  SkillsMpSkillItem,
} from "@/features/capabilities/skills/types";
import { useT } from "@/lib/i18n/client";

function getRecommendationSectionIcon(sectionKey: string) {
  if (sectionKey === "popular") return Flame;
  if (sectionKey === "recent") return Clock3;
  return Sparkles;
}

interface SkillMarketplaceBrowserProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  isSemanticSearch: boolean;
  onSemanticSearchChange: (value: boolean) => void;
  onSearch: () => void;
  onReset: () => void;
  onRefreshRecommendations: () => void;
  isLoading: boolean;
  errorMessage: string | null;
  sections: SkillsMpRecommendationSection[];
  items: SkillsMpSkillItem[];
  hasActiveSearch: boolean;
  onDownload: (item: SkillsMpSkillItem) => void;
  downloadingExternalId?: string | null;
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

function getGithubOwner(url: string | null): string | null {
  if (!url) return null;

  try {
    const parsed = new URL(url);
    if (parsed.hostname !== "github.com") return null;
    const [owner] = parsed.pathname.split("/").filter(Boolean);
    return owner ?? null;
  } catch {
    return null;
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
  const { t } = useT("translation");
  const repoLabel = getRepoLabel(item.github_url);
  const githubOwner = getGithubOwner(item.github_url);
  const avatarUrl =
    item.author_avatar_url ??
    (githubOwner ? `https://github.com/${githubOwner}.png` : null);
  const avatarFallback =
    githubOwner?.charAt(0).toUpperCase() ??
    item.author?.charAt(0).toUpperCase() ??
    item.name.charAt(0).toUpperCase();
  const isDownloading = downloadingExternalId === item.external_id;

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[1.35rem] border border-border/60 bg-gradient-to-b from-background via-background to-muted/20 shadow-[var(--shadow-sm)] transition-all duration-300 hover:-translate-y-0.5 hover:border-border hover:shadow-[var(--shadow-md)]">
      <div className="flex items-center justify-between gap-3 bg-muted/50 px-6 py-4">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {item.github_url ? (
            <a
              href={item.github_url}
              target="_blank"
              rel="noreferrer"
              className="shrink-0"
              title={repoLabel ?? item.name}
            >
              <Avatar className="size-8 border border-border/70 bg-background">
                {avatarUrl ? (
                  <AvatarImage
                    src={avatarUrl}
                    alt={repoLabel ?? item.name}
                    className="object-cover"
                  />
                ) : null}
                <AvatarFallback className="bg-muted text-xs font-semibold text-muted-foreground">
                  {avatarUrl ? avatarFallback : <Github className="size-4" />}
                </AvatarFallback>
              </Avatar>
            </a>
          ) : (
            <Avatar className="size-8 border border-border/70 bg-background">
              <AvatarFallback className="bg-muted text-xs font-semibold text-muted-foreground">
                {avatarFallback}
              </AvatarFallback>
            </Avatar>
          )}
          <h3
            className="min-w-0 flex-1 truncate text-base font-bold tracking-tight text-foreground"
            style={{
              fontFamily: '"Maple Mono", "Maple Mono NF", var(--font-mono)',
            }}
          >
            {item.name}
          </h3>
        </div>
        <div className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-amber-500/8 px-2.5 py-1 text-xs font-medium text-amber-700 dark:text-amber-300">
          <Star className="size-3.5 fill-current text-amber-500" />
          {item.stars.toLocaleString()}
        </div>
      </div>

      <div className="flex flex-1 flex-col px-5 py-4">
        <p className="line-clamp-3 min-h-[4.5rem] text-sm leading-6 text-muted-foreground">
          {item.description ||
            t("library.skillsImport.marketplace.noDescription")}
        </p>
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
  onRefreshRecommendations,
  isLoading,
  errorMessage,
  sections,
  items,
  hasActiveSearch,
  onDownload,
  downloadingExternalId,
}: SkillMarketplaceBrowserProps) {
  const { t } = useT("translation");
  const [isComposingSearch, setIsComposingSearch] = React.useState(false);

  const showEmptyState = !isLoading && !errorMessage && items.length === 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <HeaderSearchInput
          value={searchQuery}
          onChange={onSearchQueryChange}
          placeholder={t("library.skillsImport.placeholders.marketplaceSearch")}
          className="w-full md:w-full"
          onCompositionStart={() => setIsComposingSearch(true)}
          onCompositionEnd={() => setIsComposingSearch(false)}
          onKeyDown={(event) => {
            if (
              isComposingSearch ||
              event.nativeEvent.isComposing ||
              event.keyCode === 229
            ) {
              return;
            }
            if (event.key === "Enter") {
              event.preventDefault();
              onSearch();
            }
          }}
        />
        <div className="flex items-center gap-2">
          {!hasActiveSearch ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              disabled={isLoading}
              onClick={onRefreshRecommendations}
              aria-label={t("library.skillsImport.marketplace.refresh")}
              title={t("library.skillsImport.marketplace.refresh")}
            >
              <RefreshCw
                className={`size-4${isLoading ? " animate-spin" : ""}`}
              />
            </Button>
          ) : null}
          {hasActiveSearch ? (
            <Button variant="outline" onClick={onReset} disabled={isLoading}>
              {t("library.skillsImport.marketplace.reset")}
            </Button>
          ) : null}
          <Button
            type="button"
            variant={isSemanticSearch ? "default" : "outline"}
            size="icon"
            disabled={isLoading}
            onClick={() => onSemanticSearchChange(!isSemanticSearch)}
            aria-label={t("library.skillsImport.marketplace.aiSearchTooltip")}
            title={t("library.skillsImport.marketplace.aiSearchTooltip")}
          >
            <Sparkles className="size-4" />
          </Button>
          <Button onClick={onSearch} disabled={isLoading} className="shrink-0">
            <Search className="size-4" />
            {t("library.skillsImport.marketplace.search")}
          </Button>
        </div>
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
                <div>
                  <h3 className="inline-flex items-center gap-2 text-base font-semibold tracking-tight">
                    {React.createElement(
                      getRecommendationSectionIcon(section.key),
                      {
                        className: "size-4 text-muted-foreground",
                      },
                    )}
                    {section.title ||
                      t(
                        `library.skillsImport.marketplace.sections.${section.key}`,
                      )}
                  </h3>
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
                  className="grid gap-x-6 gap-y-4 sm:grid-cols-2 sm:space-y-0 md:gap-y-8"
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
