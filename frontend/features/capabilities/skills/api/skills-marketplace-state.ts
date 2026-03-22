"use client";

export const SKILLS_MARKETPLACE_CONFIG_CHANGED_EVENT =
  "poco:skills-marketplace-config-changed";

export interface SkillsMarketplaceConfigChangedDetail {
  configured: boolean;
}

export function emitSkillsMarketplaceConfigChanged(detail: {
  configured: boolean;
}): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<SkillsMarketplaceConfigChangedDetail>(
      SKILLS_MARKETPLACE_CONFIG_CHANGED_EVENT,
      { detail },
    ),
  );
}
