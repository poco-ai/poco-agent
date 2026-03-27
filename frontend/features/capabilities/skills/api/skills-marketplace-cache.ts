"use client";

import type { SkillsMpRecommendationSection } from "@/features/capabilities/skills/types";

const RECOMMENDATIONS_CACHE_SLOT = "poco_skills_marketplace_recommendations_v1";
const CACHE_TTL_MS = 8 * 60 * 60 * 1000;

interface CachedMarketplaceRecommendations {
  cached_at: number;
  sections: SkillsMpRecommendationSection[];
}

function getStorage(): Storage | null {
  if (typeof window === "undefined") return null;
  return window.localStorage;
}

export function getSkillsMarketplaceRecommendationsCacheTtlMs(): number {
  return CACHE_TTL_MS;
}

export function readCachedSkillsMarketplaceRecommendations():
  | SkillsMpRecommendationSection[]
  | null {
  const storage = getStorage();
  if (!storage) return null;

  try {
    const raw = storage.getItem(RECOMMENDATIONS_CACHE_SLOT);
    if (!raw) return null;

    const cached = JSON.parse(raw) as CachedMarketplaceRecommendations;
    if (
      !cached ||
      typeof cached.cached_at !== "number" ||
      !Array.isArray(cached.sections)
    ) {
      storage.removeItem(RECOMMENDATIONS_CACHE_SLOT);
      return null;
    }

    if (Date.now() - cached.cached_at > CACHE_TTL_MS) {
      storage.removeItem(RECOMMENDATIONS_CACHE_SLOT);
      return null;
    }

    return cached.sections;
  } catch {
    return null;
  }
}

export function writeCachedSkillsMarketplaceRecommendations(
  sections: SkillsMpRecommendationSection[],
): void {
  const storage = getStorage();
  if (!storage) return;

  try {
    const payload: CachedMarketplaceRecommendations = {
      cached_at: Date.now(),
      sections,
    };
    storage.setItem(RECOMMENDATIONS_CACHE_SLOT, JSON.stringify(payload));
  } catch {
    // Ignore localStorage write failures.
  }
}

export function clearCachedSkillsMarketplaceRecommendations(): void {
  const storage = getStorage();
  if (!storage) return;

  try {
    storage.removeItem(RECOMMENDATIONS_CACHE_SLOT);
  } catch {
    // Ignore localStorage removal failures.
  }
}
