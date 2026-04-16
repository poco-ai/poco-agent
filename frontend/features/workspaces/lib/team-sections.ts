import type * as React from "react";
import {
  Building2,
  Ticket,
  Users,
} from "lucide-react";

export type TeamSectionId = "overview" | "members" | "issues";

export interface TeamSection {
  id: TeamSectionId;
  href: string;
  label: string;
  icon?: React.ComponentType<{ className?: string }>;
}

const TEAM_SECTION_IDS: TeamSectionId[] = [
  "overview",
  "members",
  "issues",
];

const TEAM_SECTION_ICONS: Record<TeamSectionId, React.ComponentType<{ className?: string }>> = {
  overview: Building2,
  members: Users,
  issues: Ticket,
};

export function buildTeamSectionHref(
  lng: string | undefined,
  sectionId: TeamSectionId,
): string {
  const prefix = lng ? `/${lng}` : "";

  switch (sectionId) {
    case "overview":
      return `${prefix}/team`;
    case "members":
      return `${prefix}/team/members`;
    case "issues":
      return `${prefix}/team/issues`;
  }
}

export function buildTeamSections(
  lng: string | undefined,
  labels?: Partial<Record<TeamSectionId, string>>,
): TeamSection[] {
  return TEAM_SECTION_IDS.map((sectionId) => ({
    id: sectionId,
    href: buildTeamSectionHref(lng, sectionId),
    label: labels?.[sectionId] ?? sectionId,
    icon: TEAM_SECTION_ICONS[sectionId],
  }));
}

export function getTeamSectionIcon(sectionId: TeamSectionId): React.ComponentType<{ className?: string }> {
  return TEAM_SECTION_ICONS[sectionId];
}
