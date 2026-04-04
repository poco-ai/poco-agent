"use client";

import * as React from "react";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { PresetCardSurface } from "@/features/capabilities/presets/components/preset-card-surface";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { buildPresetCardBadgeLabels } from "@/features/capabilities/presets/lib/preset-card-badges";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import {
  filterProjectPresets,
  getProjectPresetCardState,
} from "@/features/projects/lib/project-preset-selection";
import { useT } from "@/lib/i18n/client";

interface ProjectSettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  projectName: string;
  projectDefaultPresetId: number | null;
  onProjectDefaultPresetChange: (presetId: number | null) => Promise<void>;
}

export function ProjectSettingsDialog({
  open,
  onOpenChange,
  projectId,
  projectName,
  projectDefaultPresetId,
  onProjectDefaultPresetChange,
}: ProjectSettingsDialogProps) {
  const { t } = useT("translation");
  const prevOpenRef = React.useRef(open);
  const [allPresets, setAllPresets] = React.useState<Preset[]>([]);
  const [searchQuery, setSearchQuery] = React.useState("");
  const [activeDefaultPresetId, setActiveDefaultPresetId] = React.useState<
    number | null
  >(projectDefaultPresetId);
  const [skillNamesById, setSkillNamesById] = React.useState<Map<number, string>>(
    () => new Map(),
  );
  const [mcpNamesById, setMcpNamesById] = React.useState<Map<number, string>>(
    () => new Map(),
  );
  const [isLoading, setIsLoading] = React.useState(false);
  const [savingKey, setSavingKey] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const presets = await presetsService.listPresets({ revalidate: 0 });
      setAllPresets(presets);
    } catch (error) {
      console.error(
        `[ProjectSettingsDialog] Failed to fetch presets for project ${projectId}`,
        error,
      );
      toast.error(t("project.settingsPanel.presets.toasts.loadError"));
    } finally {
      setIsLoading(false);
    }
  }, [projectId, t]);

  React.useEffect(() => {
    const wasOpen = prevOpenRef.current;
    prevOpenRef.current = open;

    if (!open || wasOpen) {
      return;
    }

    setSearchQuery("");
    setActiveDefaultPresetId(projectDefaultPresetId);
    void refresh();
  }, [open, projectDefaultPresetId, refresh]);

  React.useEffect(() => {
    if (!open) {
      return;
    }

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
  }, [open]);

  React.useEffect(() => {
    if (!open) return;
    setActiveDefaultPresetId(projectDefaultPresetId);
  }, [open, projectDefaultPresetId]);

  const filteredPresets = React.useMemo(() => {
    return filterProjectPresets(allPresets, searchQuery);
  }, [allPresets, searchQuery]);

  const persistDefaultPreset = React.useCallback(
    async (nextPresetId: number | null) => {
      const previousPresetId = activeDefaultPresetId;
      setSavingKey(nextPresetId === null ? "clear" : String(nextPresetId));
      setActiveDefaultPresetId(nextPresetId);

      try {
        await onProjectDefaultPresetChange(nextPresetId);
        toast.success(t("project.settingsPanel.presets.toasts.defaultUpdated"));
      } catch (error) {
        console.error(
          `[ProjectSettingsDialog] Failed to update default preset for project ${projectId}`,
          error,
        );
        setActiveDefaultPresetId(previousPresetId);
        toast.error(t("project.settingsPanel.presets.toasts.defaultFailed"));
      } finally {
        setSavingKey(null);
      }
    },
    [activeDefaultPresetId, onProjectDefaultPresetChange, projectId, t],
  );

  const handleSelectPreset = React.useCallback(
    (presetId: number) => {
      if (savingKey !== null || presetId === activeDefaultPresetId) {
        return;
      }
      void persistDefaultPreset(presetId);
    },
    [activeDefaultPresetId, persistDefaultPreset, savingKey],
  );

  const handleClearDefault = React.useCallback(() => {
    if (savingKey !== null || activeDefaultPresetId === null) {
      return;
    }
    void persistDefaultPreset(null);
  }, [activeDefaultPresetId, persistDefaultPreset, savingKey]);

  const showEmptySearch =
    !isLoading && allPresets.length > 0 && filteredPresets.length === 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <CapabilityDialogContent
        title={t("project.settingsPanel.dialogTitle", { name: projectName })}
        description={t("project.settingsPanel.dialogDescription")}
        maxWidth="48rem"
        maxHeight="80dvh"
        desktopMaxHeight="86dvh"
        footer={
          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              {t("common.close")}
            </Button>
          </DialogFooter>
        }
      >
        <div className="space-y-5">
          <section className="flex flex-col gap-3 rounded-2xl border border-border/60 bg-muted/20 p-4 sm:flex-row sm:items-center sm:justify-between">
            <HeaderSearchInput
              value={searchQuery}
              onChange={setSearchQuery}
              placeholder={t("project.settingsPanel.presets.searchPlaceholder")}
              className="w-full sm:max-w-sm"
            />
            <Button
              variant="outline"
              onClick={handleClearDefault}
              disabled={savingKey !== null || activeDefaultPresetId === null}
            >
              {t("project.settingsPanel.presets.clearDefault")}
            </Button>
          </section>

          {!isLoading &&
          allPresets.length > 0 &&
          !showEmptySearch &&
          activeDefaultPresetId === null ? (
            <div className="rounded-2xl border border-dashed border-border/60 px-4 py-3 text-sm text-muted-foreground">
              {t("project.settingsPanel.presets.empty")}
            </div>
          ) : null}

          {isLoading ? (
            <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-border/60 text-sm text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" />
              {t("project.settingsPanel.presets.loading")}
            </div>
          ) : allPresets.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-border/60 px-4 py-10 text-center text-sm text-muted-foreground">
              {t("library.presetsPage.empty")}
            </div>
          ) : showEmptySearch ? (
            <div className="rounded-2xl border border-dashed border-border/60 px-4 py-10 text-center text-sm text-muted-foreground">
              {t("project.settingsPanel.presets.emptySearch")}
            </div>
          ) : (
            <div className="grid justify-items-center gap-4">
              {filteredPresets.map((preset) => {
                const cardState = getProjectPresetCardState(
                  preset,
                  activeDefaultPresetId,
                );

                return (
                  <PresetCardSurface
                    key={preset.preset_id}
                    preset={preset}
                    selected={cardState.selected}
                    selectedVariant="primary"
                    badgeLabels={buildPresetCardBadgeLabels(preset, {
                      skillNamesById,
                      mcpNamesById,
                    })}
                    disabled={savingKey !== null}
                    onActivate={() => handleSelectPreset(preset.preset_id)}
                    className="w-full max-w-[34rem]"
                  />
                );
              })}
            </div>
          )}
        </div>
      </CapabilityDialogContent>
    </Dialog>
  );
}
