"use client";

import { useMemo, useState } from "react";
import { Bookmark, Plus } from "lucide-react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { CapabilitiesLibraryHeader } from "@/features/capabilities/components/capabilities-library-header";
import { PresetEditorPanel } from "@/features/capabilities/presets/components/preset-editor-panel";
import { PresetListItem } from "@/features/capabilities/presets/components/preset-list-item";
import { usePresetCatalog } from "@/features/capabilities/presets/hooks/use-preset-catalog";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

type PresetWorkspaceMode = "create" | "edit";

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
        : (filteredPresets.find(
            (preset) => preset.preset_id === selectedPresetId,
          ) ?? null);

    return matchedPreset ?? filteredPresets[0] ?? null;
  }, [filteredPresets, mode, selectedPresetId]);

  const activePresetId = selectedPreset?.preset_id ?? null;

  const handleCreateStart = () => {
    setMode("create");
    setSelectedPresetId(null);
  };

  const handleSelectPreset = (preset: Preset) => {
    setMode("edit");
    setSelectedPresetId(preset.preset_id);
  };

  const handleCreatePreset = async (
    ...args: Parameters<typeof store.createPreset>
  ) => {
    const created = await store.createPreset(...args);
    if (created) {
      setMode("edit");
      setSelectedPresetId(created.preset_id);
    }
    return created;
  };

  const handleUpdatePreset = async (
    ...args: Parameters<typeof store.updatePreset>
  ) => {
    const updated = await store.updatePreset(...args);
    if (updated) {
      setMode("edit");
      setSelectedPresetId(updated.preset_id);
    }
    return updated;
  };

  const handleDeletePreset = async (presetId: number) => {
    const index = filteredPresets.findIndex(
      (preset) => preset.preset_id === presetId,
    );
    const nextPreset =
      filteredPresets[index + 1] ?? filteredPresets[index - 1] ?? null;
    await store.deletePreset(presetId);
    setMode("edit");
    setSelectedPresetId(nextPreset?.preset_id ?? null);
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <CapabilitiesLibraryHeader
        title={t("library.presets.title")}
        subtitle={t("library.presets.description")}
        icon={Bookmark}
      />

      <div className="flex min-h-0 flex-1 flex-col">
        <PullToRefresh onRefresh={store.refresh} isLoading={store.isLoading}>
          <div className="flex min-h-0 flex-1 flex-col md:grid md:grid-cols-[280px_minmax(0,1fr)]">
            <section className="flex min-h-0 flex-col border-b border-border/50 md:border-b-0 md:border-r md:border-border/50">
              <div className="space-y-4 px-6 pb-4 pt-6">
                <div className="flex items-center gap-2">
                  <HeaderSearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    placeholder={t("library.presetsPage.searchPlaceholder")}
                    className="w-full"
                  />
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="shrink-0 rounded-md text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                    aria-label={t("library.presetsPage.addCard")}
                    title={t("library.presetsPage.addCard")}
                    onClick={handleCreateStart}
                  >
                    <Plus className="size-4" />
                  </Button>
                </div>

                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>
                    {t("library.presetsPage.summary", {
                      count: filteredPresets.length,
                    })}
                  </span>
                  <Badge variant="outline">{filteredPresets.length}</Badge>
                </div>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto px-3 pb-4">
                {filteredPresets.length === 0 ? (
                  <div className="flex h-full min-h-44 items-center justify-center px-4 text-center">
                    <p className="text-sm text-muted-foreground">
                      {store.presets.length === 0
                        ? t("library.presetsPage.empty")
                        : t("library.presetsPage.emptySearch")}
                    </p>
                  </div>
                ) : (
                  <div className="space-y-1">
                    {filteredPresets.map((preset) => (
                      <PresetListItem
                        key={preset.preset_id}
                        preset={preset}
                        selected={
                          mode !== "create" && preset.preset_id === activePresetId
                        }
                        onSelect={handleSelectPreset}
                      />
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="flex min-h-0 flex-1 flex-col">
              {mode === "create" ? (
                <PresetEditorPanel
                  mode="create"
                  savingKey={store.savingKey}
                  onCreate={handleCreatePreset}
                  onUpdate={handleUpdatePreset}
                  onDelete={handleDeletePreset}
                  onCancelCreate={() => {
                    setMode("edit");
                    setSelectedPresetId(filteredPresets[0]?.preset_id ?? null);
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
                <div className="flex min-h-0 flex-1 items-center justify-center px-8 text-center">
                  <div className="max-w-sm space-y-3">
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
                </div>
              )}
            </section>
          </div>
        </PullToRefresh>
      </div>
    </div>
  );
}
