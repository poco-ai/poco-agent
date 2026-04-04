import type { Preset } from "./preset-types";

interface BuildPresetCardBadgeLabelsOptions {
  skillNamesById: Map<number, string>;
  mcpNamesById: Map<number, string>;
}

function normalizeLabel(value?: string | null): string | null {
  const normalizedValue = value?.trim();
  return normalizedValue ? normalizedValue : null;
}

export function buildPresetCardBadgeLabels(
  preset: Pick<Preset, "skill_ids" | "mcp_server_ids" | "subagent_configs">,
  options: BuildPresetCardBadgeLabelsOptions,
): string[] {
  const skillLabels = preset.skill_ids
    .map((skillId) => normalizeLabel(options.skillNamesById.get(skillId)))
    .filter((label): label is string => Boolean(label));

  const mcpLabels = preset.mcp_server_ids
    .map((serverId) => normalizeLabel(options.mcpNamesById.get(serverId)))
    .filter((label): label is string => Boolean(label));

  const subagentLabels = preset.subagent_configs
    .map((config) => normalizeLabel(config.name))
    .filter((label): label is string => Boolean(label));

  const labels = [...skillLabels, ...mcpLabels, ...subagentLabels];
  const visibleLabels = labels.slice(0, 3);

  if (labels.length > 3) {
    return [...visibleLabels, "..."];
  }

  return visibleLabels;
}
