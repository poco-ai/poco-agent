"use client";

import { useMemo, useState } from "react";
import { Layers3, Plus, Sparkles } from "lucide-react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { Badge } from "@/components/ui/badge";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";
import { PresetEditorPanel } from "@/features/capabilities/presets/components/preset-editor-panel";
import { PresetListItem } from "@/features/capabilities/presets/components/preset-list-item";
import { usePresetCatalog } from "@/features/capabilities/presets/hooks/use-preset-catalog";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

type PresetWorkspaceMode = "create" | "edit";

function countEnabledPresets(
  presets: Preset[],
  key: "browser_enabled" | "memory_enabled",
): number {
  return presets.filter((preset) => preset[key]).length;
}

export function PresetsPageClient() {
  const { t } = useT("translation");
  const store = usePresetCatalog();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState<number | null>(null);
  const [mode, setMode] = useState<PresetWorkspaceMode>("edit");

  const filteredPresets = useMemo(() => {
    const collator = new Intl.Collator(undefined, { sensitivity: "base" });
    const sortedPresets = [...store.presets].sort((a, b) =>
      collator.compare(a.name, b.name),
    );

    if (!searchQuery.trim()) return sortedPresets;

    const normalizedQuery = searchQuery.trim().toLowerCase();
    return sortedPresets.filter((preset) => {
      return (
        preset.name.toLowerCase().includes(normalizedQuery) ||
        (preset.description || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [searchQuery, store.presets]);

  const selectedPreset = useMemo(() => {
    if (mode === "create") return null;

    const matchedPreset =
      selectedPresetId === null
        ? null
        : (store.presets.find((preset) => preset.preset_id === selectedPresetId) ??
          null);

    return matchedPreset ?? store.presets[0] ?? null;
  }, [mode, selectedPresetId, store.presets]);

  const activePresetId = selectedPreset?.preset_id ?? null;

  const handleCreateStart = () => {
    setMode("create");
    setSelectedPresetId(null);
  };

  const handleSelectPreset = (preset: Preset) => {
    setMode("edit");
    setSelectedPresetId(preset.preset_id);
  };

  const handleCreatePreset = async (...args: Parameters<typeof store.createPreset>) => {
    const created = await store.createPreset(...args);
    if (created) {
      setMode("edit");
      setSelectedPresetId(created.preset_id);
    }
    return created;
  };

  const handleUpdatePreset = async (...args: Parameters<typeof store.updatePreset>) => {
    const updated = await store.updatePreset(...args);
    if (updated) {
      setMode("edit");
      setSelectedPresetId(updated.preset_id);
    }
    return updated;
  };

  const handleDeletePreset = async (presetId: number) => {
    const index = store.presets.findIndex((preset) => preset.preset_id === presetId);
    const nextPreset =
      store.presets[index + 1] ?? store.presets[index - 1] ?? null;
    await store.deletePreset(presetId);
    setMode("edit");
    setSelectedPresetId(nextPreset?.preset_id ?? null);
  };

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <PullToRefresh onRefresh={store.refresh} isLoading={store.isLoading}>
        <CapabilityContentShell
          className="min-h-0 flex-1"
          contentClassName="flex min-h-0 max-w-none flex-1"
        >
          <div className="grid min-h-0 flex-1 gap-4 md:grid-cols-[220px_280px_minmax(0,1fr)]">
            <aside className="hidden min-h-0 flex-col overflow-hidden rounded-[28px] border border-border/60 bg-card/60 md:flex">
              <div className="border-b border-border/60 px-5 py-5">
                <div className="flex items-center gap-3">
                  <div className="flex size-11 items-center justify-center rounded-2xl border border-border/60 bg-background/70">
                    <Layers3 className="size-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                      {t("library.presets.title")}
                    </p>
                    <h2 className="text-lg font-semibold text-foreground">
                      {t("library.presetsPage.header.title")}
                    </h2>
                  </div>
                </div>
                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  {t("library.presets.description")}
                </p>
              </div>

              <nav className="space-y-3 px-4 py-4">
                <button
                  type="button"
                  onClick={() => {
                    if (store.presets[0]) {
                      handleSelectPreset(store.presets[0]);
                    } else {
                      setMode("edit");
                      setSelectedPresetId(null);
                    }
                  }}
                  className="flex w-full items-center justify-between rounded-2xl border border-border/60 bg-background/70 px-4 py-3 text-left transition-colors hover:bg-accent/40"
                >
                  <div>
                    <div className="text-sm font-medium text-foreground">
                      {t("library.presetsPage.panel.allPresetsLabel", "All presets")}
                    </div>
                    <div className="mt-1 text-xs text-muted-foreground">
                      {t("library.presetsPage.summary", {
                        count: store.presets.length,
                      })}
                    </div>
                  </div>
                  <Badge variant="secondary">{store.presets.length}</Badge>
                </button>

                <div className="rounded-2xl border border-border/60 bg-background/40 px-4 py-4">
                  <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <Sparkles className="size-4 text-muted-foreground" />
                    {mode === "create"
                      ? t(
                          "library.presetsPage.panel.activeDraftLabel",
                          "Draft in progress",
                        )
                      : selectedPreset
                        ? selectedPreset.name
                        : t(
                            "library.presetsPage.panel.noSelectionLabel",
                            "No preset selected",
                          )}
                  </div>
                  <p className="mt-2 text-xs leading-5 text-muted-foreground">
                    {mode === "create"
                      ? t(
                          "library.presetsPage.panel.activeDraftDescription",
                          "Use the detail drawer to define a new preset and save it into the library.",
                        )
                      : selectedPreset?.description?.trim() ||
                        t(
                          "library.presetsPage.emptyDescription",
                          "No description yet",
                        )}
                  </p>
                </div>
              </nav>

              <div className="mt-auto grid gap-3 border-t border-border/60 px-4 py-4">
                <div className="rounded-2xl border border-border/60 bg-background/60 px-4 py-3">
                  <div className="text-xs text-muted-foreground">
                    {t("library.presetsPage.flags.browser")}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-foreground">
                    {countEnabledPresets(store.presets, "browser_enabled")}
                  </div>
                </div>
                <div className="rounded-2xl border border-border/60 bg-background/60 px-4 py-3">
                  <div className="text-xs text-muted-foreground">
                    {t("library.presetsPage.flags.memory")}
                  </div>
                  <div className="mt-1 text-lg font-semibold text-foreground">
                    {countEnabledPresets(store.presets, "memory_enabled")}
                  </div>
                </div>
              </div>
            </aside>

            <section className="flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-border/60 bg-card/60">
              <div className="space-y-4 border-b border-border/60 px-4 py-4">
                <CapabilityCreateCard
                  label={t("library.presetsPage.addCard")}
                  onClick={handleCreateStart}
                  className="min-h-[56px]"
                />

                <HeaderSearchInput
                  value={searchQuery}
                  onChange={setSearchQuery}
                  placeholder={t("library.presetsPage.searchPlaceholder")}
                  className="w-full"
                />

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {t("library.presetsPage.summary", {
                      count: store.presets.length,
                    })}
                  </span>
                  <Badge variant="outline">{filteredPresets.length}</Badge>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto px-3 py-3">
                {filteredPresets.length === 0 ? (
                  <div className="flex h-full min-h-44 items-center justify-center rounded-2xl border border-dashed border-border/60 px-4 text-center">
                    <p className="text-sm text-muted-foreground">
                      {store.presets.length === 0
                        ? t("library.presetsPage.empty")
                        : t("library.presetsPage.emptySearch")}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {filteredPresets.map((preset) => (
                      <PresetListItem
                        key={preset.preset_id}
                        preset={preset}
                        selected={mode !== "create" && preset.preset_id === activePresetId}
                        onSelect={handleSelectPreset}
                      />
                    ))}
                  </div>
                )}
              </div>
            </section>

            {mode === "create" ? (
              <PresetEditorPanel
                mode="create"
                savingKey={store.savingKey}
                onCreate={handleCreatePreset}
                onUpdate={handleUpdatePreset}
                onDelete={handleDeletePreset}
                onCancelCreate={() => {
                  setMode("edit");
                  setSelectedPresetId(store.presets[0]?.preset_id ?? null);
                }}
              />
            ) : selectedPreset ? (
              <PresetEditorPanel
                mode="edit"
                preset={selectedPreset}
                savingKey={store.savingKey}
                onCreate={handleCreatePreset}
                onUpdate={handleUpdatePreset}
                onDelete={handleDeletePreset}
              />
            ) : (
              <section className="flex min-h-0 flex-1 items-center justify-center rounded-[28px] border border-dashed border-border/60 bg-card/40 px-6 text-center">
                <div className="max-w-sm space-y-3">
                  <div className="mx-auto flex size-14 items-center justify-center rounded-2xl border border-border/60 bg-background/70">
                    <Plus className="size-5 text-muted-foreground" />
                  </div>
                  <h2 className="text-lg font-semibold text-foreground">
                    {t(
                      "library.presetsPage.panel.emptyTitle",
                      "Create your first preset",
                    )}
                  </h2>
                  <p className="text-sm leading-6 text-muted-foreground">
                    {t(
                      "library.presetsPage.panel.emptyDescription",
                      "Start from the middle drawer, then configure the preset in the detail drawer.",
                    )}
                  </p>
                </div>
              </section>
            )}
          </div>
        </CapabilityContentShell>
      </PullToRefresh>
    </div>
  );
}
