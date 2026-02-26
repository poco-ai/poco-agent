"use client";

import * as React from "react";

import { Kbd } from "@/components/ui/kbd";
import { useT } from "@/lib/i18n/client";

type ShortcutItem = {
  id: string;
  action: string;
  hint: string;
  keys: string[][];
};

function ShortcutCombo({ keys }: { keys: string[] }) {
  return (
    <span className="inline-flex items-center gap-1">
      {keys.map((key, index) => (
        <React.Fragment key={`${key}-${index}`}>
          {index > 0 ? (
            <span className="text-xs text-muted-foreground">+</span>
          ) : null}
          <Kbd>{key}</Kbd>
        </React.Fragment>
      ))}
    </span>
  );
}

function ShortcutCombos({
  combos,
  orLabel,
}: {
  combos: string[][];
  orLabel: string;
}) {
  return (
    <div className="flex flex-wrap items-center justify-end gap-2">
      {combos.map((combo, index) => (
        <React.Fragment key={combo.join("-")}>
          {index > 0 ? (
            <span className="text-xs text-muted-foreground">{orLabel}</span>
          ) : null}
          <ShortcutCombo keys={combo} />
        </React.Fragment>
      ))}
    </div>
  );
}

export function ShortcutsSettingsTab() {
  const { t } = useT("translation");

  const shortcuts = React.useMemo<ShortcutItem[]>(
    () => [
      {
        id: "toggle-main-sidebar",
        action: t("settings.shortcuts.items.toggleMainSidebar.action"),
        hint: t("settings.shortcuts.items.toggleMainSidebar.hint"),
        keys: [["Ctrl", "B"]],
      },
      {
        id: "toggle-plan-mode",
        action: t("settings.shortcuts.items.togglePlanMode.action"),
        hint: t("settings.shortcuts.items.togglePlanMode.hint"),
        keys: [["Shift", "Tab"]],
      },
      {
        id: "history-prompt",
        action: t("settings.shortcuts.items.switchPromptHistory.action"),
        hint: t("settings.shortcuts.items.switchPromptHistory.hint"),
        keys: [["↑"], ["↓"]],
      },
      {
        id: "slash-command",
        action: t("settings.shortcuts.items.slashCommand.action"),
        hint: t("settings.shortcuts.items.slashCommand.hint"),
        keys: [["/"]],
      },
      {
        id: "global-search",
        action: t("settings.shortcuts.items.search.action"),
        hint: t("settings.shortcuts.items.search.hint"),
        keys: [["Ctrl", "K"]],
      },
      {
        id: "open-settings",
        action: t("settings.shortcuts.items.openSettings.action"),
        hint: t("settings.shortcuts.items.openSettings.hint"),
        keys: [["Ctrl", ","]],
      },
      {
        id: "toggle-right-panel",
        action: t("settings.shortcuts.items.toggleOutputPanel.action"),
        hint: t("settings.shortcuts.items.toggleOutputPanel.hint"),
        keys: [["Ctrl", "L"]],
      },
      {
        id: "jump-user-prompts",
        action: t("settings.shortcuts.items.jumpUserPrompts.action"),
        hint: t("settings.shortcuts.items.jumpUserPrompts.hint"),
        keys: [["J"], ["K"]],
      },
    ],
    [t],
  );

  const orLabel = t("settings.shortcuts.or");

  return (
    <div className="flex-1 overflow-y-auto p-5">
      <div className="overflow-hidden rounded-xl border border-border bg-card">
        <div className="divide-y divide-border">
          {shortcuts.map((shortcut) => {
            return (
              <div
                key={shortcut.id}
                className="flex items-center justify-between gap-4 p-4"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm leading-5 font-medium text-foreground">
                    {shortcut.action}
                  </p>
                  <p className="mt-1 text-xs leading-4 text-muted-foreground">
                    {shortcut.hint}
                  </p>
                </div>

                <div className="shrink-0 flex items-center">
                  <ShortcutCombos combos={shortcut.keys} orLabel={orLabel} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
