"use client";

import * as React from "react";
import type { LucideIcon } from "lucide-react";
import {
  Store,
  Puzzle,
  Plug,
  Server,
  KeySquare,
  FileText,
  Command as CommandIcon,
  Bot,
} from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { SkillsMarketplacePageClient } from "@/features/capabilities/marketplace/components/skills-marketplace-page-client";
import { SkillsPageClient } from "@/features/capabilities/skills/components/skills-page-client";
import { McpPageClient } from "@/features/capabilities/mcp/components/mcp-page-client";
import { PluginsPageClient } from "@/features/capabilities/plugins/components/plugins-page-client";
import { EnvVarsPageClient } from "@/features/capabilities/env-vars/components/env-vars-page-client";
import { PersonalizationPageClient } from "@/features/capabilities/personalization/components/personalization-page-client";
import { SlashCommandsPageClient } from "@/features/capabilities/slash-commands/components/slash-commands-page-client";
import { SubAgentsPageClient } from "@/features/capabilities/sub-agents/components/sub-agents-page-client";

export interface CapabilityView {
  id: string;
  label: string;
  description: string;
  group: "featured" | "primary" | "secondary" | "tertiary";
  icon: LucideIcon;
  component: React.ComponentType;
}

export function useCapabilityViews(): CapabilityView[] {
  const { t } = useT("translation");

  return React.useMemo(
    () => [
      {
        id: "marketplace",
        label: t("library.skillsImport.tabs.marketplace", "Marketplace"),
        description: t(
          "library.skillsImport.hints.marketplace",
          "Discover SkillsMP skills through recommendations or search, then continue with Poco's existing import flow.",
        ),
        group: "featured",
        icon: Store,
        component: SkillsMarketplacePageClient,
      },
      {
        id: "skills",
        label: t("library.skillsStore.title"),
        description: t("library.skillsStore.description"),
        group: "primary",
        icon: Puzzle,
        component: SkillsPageClient,
      },
      {
        id: "mcp",
        label: t("library.mcpInstall.title"),
        description: t("library.mcpInstall.description"),
        group: "primary",
        icon: Server,
        component: McpPageClient,
      },
      {
        id: "plugins",
        label: t("library.pluginsManager.title"),
        description: t("library.pluginsManager.description"),
        group: "primary",
        icon: Plug,
        component: PluginsPageClient,
      },
      {
        id: "slash-commands",
        label: t("library.slashCommands.card.title", "Slash Commands"),
        description: t(
          "library.slashCommands.card.description",
          "Save reusable shortcuts",
        ),
        group: "primary",
        icon: CommandIcon,
        component: SlashCommandsPageClient,
      },
      {
        id: "sub-agents",
        label: t("library.subAgents.card.title", "Sub-agents"),
        description: t(
          "library.subAgents.card.description",
          "Create specialized copilots",
        ),
        group: "secondary",
        icon: Bot,
        component: SubAgentsPageClient,
      },
      {
        id: "env",
        label: t("library.envVars.sidebarTitle", "Environment Variables"),
        description: t(
          "library.envVars.description",
          "Manage API keys and secrets",
        ),
        group: "tertiary",
        icon: KeySquare,
        component: EnvVarsPageClient,
      },
      {
        id: "personalization",
        label: t("library.personalization.card.title", "Personalization"),
        description: t(
          "library.personalization.card.description",
          "Set persistent preferences",
        ),
        group: "tertiary",
        icon: FileText,
        component: PersonalizationPageClient,
      },
    ],
    [t],
  );
}
