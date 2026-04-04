"use client";

import { useEffect, useMemo, useState } from "react";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { CapabilityCreateCard } from "@/features/capabilities/components/capability-create-card";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { PresetCard } from "@/features/capabilities/presets/components/preset-card";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { buildPresetCardBadgeLabels } from "@/features/capabilities/presets/lib/preset-card-badges";
import {
  PresetFormDialog,
  type PresetDialogMode,
} from "@/features/capabilities/presets/components/preset-form-dialog";
import { usePresetCatalog } from "@/features/capabilities/presets/hooks/use-preset-catalog";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

export function PresetsPageClient() {
  const { t } = useT("translation");
  const store = usePresetCatalog();
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<PresetDialogMode>("create");
  const [editing, setEditing] = useState<Preset | null>(null);
  const [skillNamesById, setSkillNamesById] = useState<Map<number, string>>(
    () => new Map(),
  );
  const [mcpNamesById, setMcpNamesById] = useState<Map<number, string>>(
    () => new Map(),
  );

  useEffect(() => {
    let active = true;

    void Promise.all([
      skillsService.listSkills({ revalidate: 0 }),
      mcpService.listServers({ revalidate: 0 }),
    ]).then(([skills, servers]) => {
      if (!active) return;
      setSkillNamesById(new Map(skills.map((skill) => [skill.id, skill.name])));
      setMcpNamesById(
        new Map(servers.map((server) => [server.id, server.name])),
      );
    });

    return () => {
      active = false;
    };
  }, []);

  const filteredPresets = useMemo(() => {
    if (!searchQuery.trim()) return store.presets;
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return store.presets.filter((preset) => {
      return (
        preset.name.toLowerCase().includes(normalizedQuery) ||
        (preset.description || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [searchQuery, store.presets]);

  return (
    <>
      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh onRefresh={store.refresh} isLoading={store.isLoading}>
          <CapabilityContentShell>
            <div className="space-y-6">
              <div className="rounded-xl bg-muted/50 px-5 py-3">
                <div className="flex flex-wrap items-center gap-3 md:justify-between">
                  <p className="text-sm text-muted-foreground">
                    {t("library.presetsPage.summary", {
                      count: store.presets.length,
                    })}
                  </p>
                  <HeaderSearchInput
                    value={searchQuery}
                    onChange={setSearchQuery}
                    placeholder={t("library.presetsPage.searchPlaceholder")}
                    className="w-full md:w-64"
                  />
                </div>
              </div>

              <div className="space-y-3">
                <CapabilityCreateCard
                  label={t("library.presetsPage.addCard")}
                  onClick={() => {
                    setDialogMode("create");
                    setEditing(null);
                    setDialogOpen(true);
                  }}
                />

                {store.isLoading && store.presets.length === 0 ? null : null}

                {filteredPresets.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-border/60 px-4 py-10 text-center">
                    <p className="text-sm text-muted-foreground">
                      {store.presets.length === 0
                        ? t("library.presetsPage.empty")
                        : t("library.presetsPage.emptySearch")}
                    </p>
                  </div>
                ) : (
                  <div className="grid gap-4 lg:grid-cols-2">
                    {filteredPresets.map((preset) => (
                      <PresetCard
                        key={preset.preset_id}
                        preset={preset}
                        badgeLabels={buildPresetCardBadgeLabels(preset, {
                          skillNamesById,
                          mcpNamesById,
                        })}
                        onEdit={(targetPreset) => {
                          setDialogMode("edit");
                          setEditing(targetPreset);
                          setDialogOpen(true);
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CapabilityContentShell>
        </PullToRefresh>
      </div>

      <PresetFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        initialPreset={editing}
        savingKey={store.savingKey}
        onCreate={store.createPreset}
        onUpdate={store.updatePreset}
        onDelete={store.deletePreset}
      />
    </>
  );
}
