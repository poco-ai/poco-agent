import test from "node:test";
import assert from "node:assert/strict";

import type { Preset } from "./preset-types.ts";
import { buildPresetCardBadgeLabels } from "./preset-card-badges.ts";

function createPreset(overrides: Partial<Preset> = {}): Preset {
  return {
    preset_id: 1,
    user_id: "user-1",
    name: "Code review",
    description: "Review backend services",
    visual_key: "preset-visual-01",
    visual_url: "https://example.com/preset.svg",
    visual_version: "abc123",
    visual_name: "Preset Visual 01",
    prompt_template: "",
    skill_ids: [11, 12],
    mcp_server_ids: [21, 22],
    plugin_ids: [],
    subagent_configs: [{ name: "Reviewer" }, { name: "Planner" }],
    browser_enabled: false,
    memory_enabled: false,
    created_at: "2026-04-02T00:00:00Z",
    updated_at: "2026-04-02T00:00:00Z",
    ...overrides,
  };
}

test("buildPresetCardBadgeLabels prefers skill, then mcp, then subagent names", () => {
  const preset = createPreset();

  assert.deepEqual(
    buildPresetCardBadgeLabels(preset, {
      skillNamesById: new Map([
        [11, "Python"],
        [12, "Code review"],
      ]),
      mcpNamesById: new Map([
        [21, "GitHub"],
        [22, "Notion"],
      ]),
    }),
    ["Python", "Code review", "GitHub", "..."],
  );
});

test("buildPresetCardBadgeLabels skips missing names and trims blanks", () => {
  const preset = createPreset({
    skill_ids: [11],
    mcp_server_ids: [21],
    subagent_configs: [{ name: "  Planner  " }, { name: "   " }],
  });

  assert.deepEqual(
    buildPresetCardBadgeLabels(preset, {
      skillNamesById: new Map(),
      mcpNamesById: new Map([[21, "GitHub"]]),
    }),
    ["GitHub", "Planner"],
  );
});

test("buildPresetCardBadgeLabels keeps at most three names before overflow", () => {
  const preset = createPreset({
    skill_ids: [11, 12, 13],
    mcp_server_ids: [21, 22],
    subagent_configs: [{ name: "Reviewer" }],
  });

  assert.deepEqual(
    buildPresetCardBadgeLabels(preset, {
      skillNamesById: new Map([
        [11, "Python"],
        [12, "Code review"],
        [13, "Refactor"],
      ]),
      mcpNamesById: new Map([
        [21, "GitHub"],
        [22, "Notion"],
      ]),
    }),
    ["Python", "Code review", "Refactor", "..."],
  );
});
