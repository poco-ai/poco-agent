import * as React from "react";
import { PresetCard } from "@/features/capabilities/presets/components/preset-card";
import { PresetFormDialog } from "@/features/capabilities/presets/components/preset-form-dialog";
import { buildPresetCardBadgeLabels } from "@/features/capabilities/presets/lib/preset-card-badges";
import type {
  Preset,
  PresetCapabilityItem,
  PresetCreateInput,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";
import type { Skill } from "@/features/capabilities/skills/types";
import type {
  AdminMcpServer,
  AdminPlugin,
} from "@/features/settings/api/admin-api";
import type { PresetVisualOption } from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

import { AdminSectionError, AdminSectionLoading } from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface AdminPresetsSectionProps {
  presets: Preset[];
  skills: Skill[];
  mcpServers: AdminMcpServer[];
  plugins: AdminPlugin[];
  presetVisuals: PresetVisualOption[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: PresetCreateInput) => Promise<void>;
  onUpdate: (presetId: number, input: PresetUpdateInput) => Promise<void>;
  onDelete: (presetId: number) => Promise<void>;
}

export function AdminPresetsSection({
  presets,
  skills,
  mcpServers,
  plugins,
  presetVisuals,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminPresetsSectionProps) {
  const { t } = useT("translation");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingPreset, setEditingPreset] = React.useState<Preset | null>(null);
  const [searchQuery, setSearchQuery] = React.useState("");

  const capabilityItemsOverride = React.useMemo<{
    skills: PresetCapabilityItem[];
    mcp: PresetCapabilityItem[];
    plugins: PresetCapabilityItem[];
  }>(
    () => ({
      skills: skills
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
      mcp: mcpServers
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
      plugins: plugins
        .filter((item) => item.scope === "system")
        .map((item) => ({
          id: item.id,
          name: item.name,
          description: item.description,
          scope: item.scope,
        })),
    }),
    [mcpServers, plugins, skills],
  );

  const skillNamesById = React.useMemo(
    () => new Map(skills.map((skill) => [skill.id, skill.name])),
    [skills],
  );
  const mcpNamesById = React.useMemo(
    () => new Map(mcpServers.map((server) => [server.id, server.name])),
    [mcpServers],
  );

  const filteredPresets = React.useMemo(() => {
    if (!searchQuery.trim()) return presets;
    const normalizedQuery = searchQuery.trim().toLowerCase();
    return presets.filter((preset) => {
      return (
        preset.name.toLowerCase().includes(normalizedQuery) ||
        (preset.description || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [presets, searchQuery]);

  const handleCreate = React.useCallback(
    async (input: PresetCreateInput) => {
      await onCreate(input);
      setDialogOpen(false);
      setEditingPreset(null);
      return null;
    },
    [onCreate],
  );

  const handleUpdate = React.useCallback(
    async (presetId: number, input: PresetUpdateInput) => {
      await onUpdate(presetId, input);
      setDialogOpen(false);
      setEditingPreset(null);
      return null;
    },
    [onUpdate],
  );

  const handleDelete = React.useCallback(
    async (presetId: number) => {
      await onDelete(presetId);
      setDialogOpen(false);
      setEditingPreset(null);
    },
    [onDelete],
  );

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.presetsTitle")}
        description={t("settings.admin.presetsDescription")}
        summary={t("library.presetsPage.summary", { count: presets.length })}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.presetsPage.searchPlaceholder")}
        createLabel={t("library.presetsPage.addCard")}
        onCreate={() => {
          setEditingPreset(null);
          setDialogOpen(true);
        }}
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <div className="space-y-6">
            <div className="space-y-3">
              {filteredPresets.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-border/60 px-4 py-10 text-center">
                  <p className="text-sm text-muted-foreground">
                    {presets.length === 0
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
                        setEditingPreset(targetPreset);
                        setDialogOpen(true);
                      }}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </AdminCatalogShell>

      <PresetFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={editingPreset ? "edit" : "create"}
        initialPreset={editingPreset}
        capabilityItemsOverride={capabilityItemsOverride}
        visualOptionsOverride={presetVisuals}
        savingKey={
          isSaving
            ? editingPreset
              ? String(editingPreset.preset_id)
              : "create"
            : null
        }
        onCreate={handleCreate}
        onUpdate={handleUpdate}
        onDelete={handleDelete}
      />
    </>
  );
}
