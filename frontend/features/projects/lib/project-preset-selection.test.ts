import test from "node:test";
import assert from "node:assert/strict";

import type { Preset } from "../../capabilities/presets/lib/preset-types.ts";
import {
  filterProjectPresets,
  getProjectPresetCardState,
} from "./project-preset-selection.ts";

function createPreset(overrides: Partial<Preset>): Preset {
  return {
    preset_id: 1,
    user_id: "user-1",
    name: "Code review",
    description: "Review backend services",
    icon: "code",
    color: "#3b82f6",
    prompt_template: "",
    skill_ids: [],
    mcp_server_ids: [],
    plugin_ids: [],
    subagent_configs: [],
    browser_enabled: false,
    memory_enabled: false,
    created_at: "2026-04-02T00:00:00Z",
    updated_at: "2026-04-02T00:00:00Z",
    ...overrides,
  };
}

test("filterProjectPresets matches both name and description", () => {
  const presets = [
    createPreset({ preset_id: 1, name: "Code review" }),
    createPreset({
      preset_id: 2,
      name: "Planner",
      description: "Write implementation plans",
    }),
  ];

  assert.deepEqual(
    filterProjectPresets(presets, "plan").map((preset) => preset.preset_id),
    [2],
  );
  assert.deepEqual(
    filterProjectPresets(presets, "review").map((preset) => preset.preset_id),
    [1],
  );
});

test("getProjectPresetCardState keeps selected preset on its own accent tint", () => {
  const preset = createPreset({ preset_id: 3, color: "#f97316" });

  assert.deepEqual(getProjectPresetCardState(preset, 3), {
    selected: true,
    iconTone: "accent",
    cardBackgroundColor: "#f9731610",
  });
});

test("getProjectPresetCardState mutes unselected presets", () => {
  const preset = createPreset({ preset_id: 4, color: "#22c55e" });

  assert.deepEqual(getProjectPresetCardState(preset, 2), {
    selected: false,
    iconTone: "muted",
  });
});

test("getProjectPresetCardState falls back to primary tint when preset color is missing", () => {
  const preset = createPreset({ preset_id: 5, color: null });

  assert.deepEqual(getProjectPresetCardState(preset, 5), {
    selected: true,
    iconTone: "accent",
    cardBackgroundColor: "color-mix(in srgb, var(--primary) 10%, transparent)",
  });
});
