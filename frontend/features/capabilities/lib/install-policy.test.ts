import test from "node:test";
import assert from "node:assert/strict";

import { getEffectiveInstallState } from "./install-policy.ts";

test("treats default-enabled system capabilities without installs as enabled", () => {
  const state = getEffectiveInstallState(
    {
      scope: "system",
      default_enabled: true,
      force_enabled: false,
    },
    null,
  );

  assert.equal(state.autoEnabled, true);
  assert.equal(state.isInstalled, true);
  assert.equal(state.isEnabled, true);
});

test("prefers persisted install records over policy defaults", () => {
  const state = getEffectiveInstallState(
    {
      scope: "system",
      default_enabled: true,
      force_enabled: false,
    },
    {
      id: 12,
      enabled: false,
    },
  );

  assert.equal(state.autoEnabled, false);
  assert.equal(state.hasInstall, true);
  assert.equal(state.isInstalled, true);
  assert.equal(state.isEnabled, false);
});
