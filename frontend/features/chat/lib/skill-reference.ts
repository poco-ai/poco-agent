import type { Skill } from "@/features/capabilities/skills/types";
import type { ChatSkillReference } from "@/features/chat/types/api/session";

export type SkillReferenceTriggerSymbol = "/" | "$";

export interface SkillReferenceTrigger {
  start: number;
  end: number;
  query: string;
  symbol: SkillReferenceTriggerSymbol;
}

export interface SkillReferenceCandidate {
  id: string;
  skill: Skill;
  displayName: string;
  description: string | null;
}

export interface InsertSkillReferenceResult {
  value: string;
  cursor: number;
  reference: ChatSkillReference;
}

const SKILL_TRIGGER_RE = /(?:^|\s)([/$])([^\s/$@#]*)$/;

function normalizeSkillName(skill: Skill): string {
  return skill.name.trim();
}

function matchesQuery(skill: Skill, query: string): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;
  return (
    skill.name.toLowerCase().includes(normalizedQuery) ||
    (skill.description ?? "").toLowerCase().includes(normalizedQuery)
  );
}

export function getSkillReferenceTrigger(
  value: string,
  cursor: number,
): SkillReferenceTrigger | null {
  const boundedCursor = Math.max(0, Math.min(cursor, value.length));
  const beforeCursor = value.slice(0, boundedCursor);
  const match = beforeCursor.match(SKILL_TRIGGER_RE);
  if (!match || !match[1]) return null;

  const tokenStart = beforeCursor.length - match[0].length;
  const symbolOffset = match[0].indexOf(match[1]);
  const start = tokenStart + symbolOffset;

  return {
    start,
    end: boundedCursor,
    query: match[2] ?? "",
    symbol: match[1] as SkillReferenceTriggerSymbol,
  };
}

export function getSkillReferenceCandidates(
  skills: Skill[],
  query: string,
): SkillReferenceCandidate[] {
  const seenIds = new Set<number>();
  const candidates: SkillReferenceCandidate[] = [];

  for (const skill of skills) {
    const name = normalizeSkillName(skill);
    if (!name || skill.admin_disabled || seenIds.has(skill.id)) continue;
    if (!matchesQuery(skill, query)) continue;

    candidates.push({
      id: `skill:${skill.id}`,
      skill,
      displayName: name,
      description: skill.description,
    });
    seenIds.add(skill.id);
  }

  return candidates.sort((left, right) =>
    left.displayName.localeCompare(right.displayName),
  );
}

export function insertSkillReference(
  value: string,
  selectionStart: number,
  selectionEnd: number,
  candidate: SkillReferenceCandidate,
): InsertSkillReferenceResult | null {
  const trigger = getSkillReferenceTrigger(value, selectionStart);
  if (!trigger) return null;

  const insertedText = `${trigger.symbol}${candidate.displayName}`;
  const replacement = `${insertedText} `;
  const start = trigger.start;
  const end = Math.max(trigger.end, selectionEnd);
  const nextValue = `${value.slice(0, start)}${replacement}${value.slice(end)}`;
  const rangeEnd = start + insertedText.length;

  return {
    value: nextValue,
    cursor: start + replacement.length,
    reference: {
      id: `skill:${candidate.skill.id}:${start}:${rangeEnd}`,
      kind: "skill",
      skillId: candidate.skill.id,
      insertedText,
      displayName: candidate.displayName,
      range: { start, end: rangeEnd },
      metadata: {
        trigger: trigger.symbol,
        description: candidate.description,
      },
    },
  };
}

export function filterSkillReferences(
  references: ChatSkillReference[] | undefined,
  value: string,
  skills: Skill[],
): ChatSkillReference[] {
  if (!references?.length) return [];

  const availableSkillIds = new Set(
    skills.filter((skill) => !skill.admin_disabled).map((skill) => skill.id),
  );

  const nextReferences: ChatSkillReference[] = [];
  for (const reference of references) {
    const insertedText = reference.insertedText.trim();
    if (!insertedText || !availableSkillIds.has(reference.skillId)) continue;

    const start =
      reference.range &&
      value.slice(reference.range.start, reference.range.end) === insertedText
        ? reference.range.start
        : value.indexOf(insertedText);
    if (start === -1) continue;

    nextReferences.push({
      ...reference,
      range: {
        start,
        end: start + insertedText.length,
      },
    });
  }

  return nextReferences;
}

export function getReferencedSkillConfig(
  references: ChatSkillReference[] | undefined,
): Record<string, boolean> {
  const config: Record<string, boolean> = {};
  for (const reference of references ?? []) {
    config[String(reference.skillId)] = true;
  }
  return config;
}
