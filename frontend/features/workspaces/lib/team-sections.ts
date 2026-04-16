export type TeamSectionId = "overview" | "members" | "invites" | "issues";

export interface TeamSection {
  id: TeamSectionId;
  href: string;
}

const TEAM_SECTION_IDS: TeamSectionId[] = [
  "overview",
  "members",
  "invites",
  "issues",
];

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
    case "invites":
      return `${prefix}/team/invites`;
    case "issues":
      return `${prefix}/team/issues`;
  }
}

export function buildTeamSections(lng: string | undefined): TeamSection[] {
  return TEAM_SECTION_IDS.map((sectionId) => ({
    id: sectionId,
    href: buildTeamSectionHref(lng, sectionId),
  }));
}
