import type { Skill } from "@/features/capabilities/skills/types";

export const RECOMMENDED_USER_SKILL_LIMIT = 5;

export function countsTowardRecommendedSkillLimit(
  skill: Pick<Skill, "scope" | "admin_disabled"> | null | undefined,
): boolean {
  if (!skill || skill.admin_disabled) {
    return false;
  }

  return skill.scope !== "system";
}
