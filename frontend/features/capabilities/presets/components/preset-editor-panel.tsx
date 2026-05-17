"use client";

import * as React from "react";
import Image from "next/image";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import { CapabilitySelector } from "@/features/capabilities/presets/components/capability-selector";
import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import {
  getPresetFormInitialVisualKey,
  isPresetFormValid,
} from "@/features/capabilities/presets/lib/preset-form";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import type {
  Preset,
  PresetCapabilityItem,
  PresetCreateInput,
  PresetSubAgentConfig,
  PresetVisualOption,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { useT } from "@/lib/i18n/client";

type PresetPanelMode = "create" | "edit";

interface PresetEditorPanelProps {
  mode: PresetPanelMode;
  preset?: Preset | null;
  savingKey?: string | null;
  onCreate: (input: PresetCreateInput) => Promise<Preset | null | void>;
  onUpdate: (
    presetId: number,
    input: PresetUpdateInput,
  ) => Promise<Preset | null | void>;
  onDelete?: (presetId: number) => Promise<void>;
  onCancelCreate?: () => void;
}

const SUBAGENT_MODELS = ["inherit", "sonnet", "opus", "haiku"] as const;

function normalizeSubagentConfig(
  value?: PresetSubAgentConfig[],
): PresetSubAgentConfig[] {
  return value?.map((item) => ({ ...item, tools: item.tools ?? null })) ?? [];
}

function parseTools(raw: string): string[] | null {
  const items = raw
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
  return items.length > 0 ? items : null;
}

function formatTimestamp(value?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function PresetEditorPanel({
  mode,
  preset,
  savingKey,
  onCreate,
  onUpdate,
  onDelete,
  onCancelCreate,
}: PresetEditorPanelProps) {
  const { t } = useT("translation");
  const [capabilityItems, setCapabilityItems] = React.useState<{
    skills: PresetCapabilityItem[];
    mcp: PresetCapabilityItem[];
    plugins: PresetCapabilityItem[];
  }>({
    skills: [],
    mcp: [],
    plugins: [],
  });
  const [visualOptions, setVisualOptions] = React.useState<
    PresetVisualOption[]
  >([]);
  const [isLoadingCapabilities, setIsLoadingCapabilities] =
    React.useState(false);
  const [isLoadingVisualOptions, setIsLoadingVisualOptions] =
    React.useState(false);

  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [visualKey, setVisualKey] = React.useState(
    getPresetFormInitialVisualKey(),
  );
  const [promptTemplate, setPromptTemplate] = React.useState("");
  const [browserEnabled, setBrowserEnabled] = React.useState(false);
  const [memoryEnabled, setMemoryEnabled] = React.useState(false);
  const [skillIds, setSkillIds] = React.useState<number[]>([]);
  const [mcpServerIds, setMcpServerIds] = React.useState<number[]>([]);
  const [pluginIds, setPluginIds] = React.useState<number[]>([]);
  const [subagentConfigs, setSubagentConfigs] = React.useState<
    PresetSubAgentConfig[]
  >([]);
  const [activeTab, setActiveTab] = React.useState("general");
  const [visualDialogOpen, setVisualDialogOpen] = React.useState(false);
  const [draftVisualKey, setDraftVisualKey] = React.useState(
    getPresetFormInitialVisualKey(),
  );

  React.useEffect(() => {
    if (mode === "edit" && preset) {
      setName(preset.name);
      setDescription(preset.description || "");
      setVisualKey(getPresetFormInitialVisualKey(preset.visual_key));
      setPromptTemplate(preset.prompt_template || "");
      setBrowserEnabled(preset.browser_enabled);
      setMemoryEnabled(preset.memory_enabled);
      setSkillIds(preset.skill_ids);
      setMcpServerIds(preset.mcp_server_ids);
      setPluginIds(preset.plugin_ids);
      setSubagentConfigs(normalizeSubagentConfig(preset.subagent_configs));
      return;
    }

    setName("");
    setDescription("");
    setVisualKey(getPresetFormInitialVisualKey());
    setPromptTemplate("");
    setBrowserEnabled(false);
    setMemoryEnabled(false);
    setSkillIds([]);
    setMcpServerIds([]);
    setPluginIds([]);
    setSubagentConfigs([]);
  }, [mode, preset]);

  React.useEffect(() => {
    if (!visualDialogOpen) return;
    setDraftVisualKey(visualKey);
  }, [visualDialogOpen, visualKey]);

  React.useEffect(() => {
    let active = true;

    const loadPanelData = async () => {
      setIsLoadingCapabilities(true);
      setIsLoadingVisualOptions(true);
      try {
        const [skills, servers, plugins, visuals] = await Promise.all([
          skillsService.listSkills({ revalidate: 0 }),
          mcpService.listServers({ revalidate: 0 }),
          pluginsService.listPlugins({ revalidate: 0 }),
          presetsService.listPresetVisuals({ revalidate: 0 }),
        ]);
        if (!active) return;
        setCapabilityItems({
          skills: skills.map((skill) => ({
            id: skill.id,
            name: skill.name,
            description: skill.description,
            scope: skill.scope,
          })),
          mcp: servers.map((server) => ({
            id: server.id,
            name: server.name,
            description: server.description,
            scope: server.scope,
          })),
          plugins: plugins.map((plugin) => ({
            id: plugin.id,
            name: plugin.name,
            description: plugin.description,
            scope: plugin.scope,
          })),
        });
        setVisualOptions(visuals);
      } catch (error) {
        console.error(
          "[PresetEditorPanel] Failed to load preset panel data",
          error,
        );
      } finally {
        if (active) {
          setIsLoadingCapabilities(false);
          setIsLoadingVisualOptions(false);
        }
      }
    };

    void loadPanelData();
    return () => {
      active = false;
    };
  }, []);

  const isSaving =
    mode === "create" ? savingKey === "create" : savingKey === String(preset?.preset_id);
  const isValid = isPresetFormValid({ name, visualKey });

  const selectedVisualOption = React.useMemo(
    () =>
      visualOptions.find((option) => option.key === visualKey) ??
      (preset
        ? {
            key: preset.visual_key,
            name: preset.visual_name,
            url: preset.visual_url,
          }
        : null),
    [preset, visualKey, visualOptions],
  );

  const handleDelete = React.useCallback(async () => {
    if (!preset || !onDelete) return;
    await onDelete(preset.preset_id);
  }, [onDelete, preset]);

  const handleSubmit = React.useCallback(async () => {
    if (!isValid) return null;

    const payload: PresetCreateInput = {
      name: name.trim(),
      description: description.trim() || null,
      visual_key: visualKey.trim(),
      prompt_template: promptTemplate.trim() || null,
      browser_enabled: browserEnabled,
      memory_enabled: memoryEnabled,
      skill_ids: skillIds,
      mcp_server_ids: mcpServerIds,
      plugin_ids: pluginIds,
      subagent_configs: subagentConfigs.map((config) => ({
        name: config.name.trim(),
        description: config.description?.trim() || null,
        prompt: config.prompt?.trim() || null,
        model: config.model || null,
        tools: config.tools?.length ? config.tools : null,
      })),
    };

    if (mode === "create") {
      return onCreate(payload);
    }
    if (!preset) return null;
    return onUpdate(preset.preset_id, payload);
  }, [
    browserEnabled,
    isValid,
    mcpServerIds,
    memoryEnabled,
    mode,
    name,
    onCreate,
    onUpdate,
    pluginIds,
    preset,
    promptTemplate,
    skillIds,
    subagentConfigs,
    visualKey,
    description,
  ]);

  const detailPreset = preset ?? {
    name: name || t("library.presetsPage.panel.newPresetLabel", "New preset"),
    visual_key: visualKey,
    visual_url: selectedVisualOption?.url ?? null,
  };

  const headerName =
    name.trim() || t("library.presetsPage.panel.newPresetLabel", "New preset");
  const headerDescription =
    description.trim() ||
    t(
      "library.presetsPage.panel.headerDescriptionFallback",
      "No description yet",
    );

  const handleVisualApply = React.useCallback(() => {
    setVisualKey(draftVisualKey);
    setVisualDialogOpen(false);
  }, [draftVisualKey]);

  return (
    <>
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border/50 px-6 pb-5 pt-6">
        <div className="flex items-start gap-4">
          <button
            type="button"
            onClick={() => setVisualDialogOpen(true)}
            className="shrink-0 rounded-[28px] transition-opacity hover:opacity-85"
            aria-label={t(
              "library.presetsPage.panel.changeVisual",
              "Change preset avatar",
            )}
          >
            <PresetGlyph preset={detailPreset} variant="card" />
          </button>
          <div className="min-w-0 space-y-1">
            <h2 className="truncate text-xl font-semibold text-foreground">
              {headerName}
            </h2>
            <p className="line-clamp-2 text-sm leading-6 text-muted-foreground">
              {headerDescription}
            </p>
          </div>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="flex flex-col gap-5"
        >
          <TabsList className="w-full justify-start overflow-x-auto">
            <TabsTrigger value="general">
              {t("library.presetsPage.tabs.general")}
            </TabsTrigger>
            <TabsTrigger value="capabilities">
              {t("library.presetsPage.tabs.capabilities")}
            </TabsTrigger>
            <TabsTrigger value="subagents">
              {t("library.presetsPage.tabs.subagents")}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-5">
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="preset-name-inline">
                  {t("library.presetsPage.form.name")}
                </Label>
                <Input
                  id="preset-name-inline"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder={t("library.presetsPage.form.namePlaceholder")}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="preset-description-inline">
                  {t("library.presetsPage.form.description")}
                </Label>
                <Textarea
                  id="preset-description-inline"
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder={t(
                    "library.presetsPage.form.descriptionPlaceholder",
                  )}
                  rows={4}
                />
              </div>
              {mode === "edit" && preset ? (
                <div className="space-y-2">
                  <Label>{t("library.presetsPage.panel.createdLabel", "Created")}</Label>
                  <div className="rounded-md border border-border/50 bg-background/40 px-3 py-2 text-sm text-muted-foreground">
                    {formatTimestamp(preset.created_at) ?? "—"}
                  </div>
                </div>
              ) : null}
              <div className="space-y-2">
                <Label htmlFor="preset-prompt-inline">
                  {t("library.presetsPage.form.promptTemplate")}
                </Label>
                <Textarea
                  id="preset-prompt-inline"
                  value={promptTemplate}
                  onChange={(event) => setPromptTemplate(event.target.value)}
                  placeholder={t(
                    "library.presetsPage.form.promptTemplatePlaceholder",
                  )}
                  rows={10}
                />
              </div>
              <div className="space-y-3 rounded-2xl border border-border/60 bg-background/40 p-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {t("library.presetsPage.form.browserEnabled")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("library.presetsPage.form.browserEnabledHint")}
                    </p>
                  </div>
                  <Switch
                    checked={browserEnabled}
                    onCheckedChange={setBrowserEnabled}
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {t("library.presetsPage.form.memoryEnabled")}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t("library.presetsPage.form.memoryEnabledHint")}
                    </p>
                  </div>
                  <Switch
                    checked={memoryEnabled}
                    onCheckedChange={setMemoryEnabled}
                  />
                </div>
              </div>
              <div className="flex flex-wrap justify-end gap-2 border-t border-border/50 pt-4">
                {mode === "create" && onCancelCreate ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={onCancelCreate}
                    disabled={isSaving}
                  >
                    {t("common.cancel")}
                  </Button>
                ) : null}
                {mode === "edit" && preset && onDelete ? (
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      void handleDelete();
                    }}
                    disabled={isSaving}
                    className="text-destructive hover:text-destructive"
                  >
                    <Trash2 className="mr-2 size-4" />
                    {t("common.delete")}
                  </Button>
                ) : null}
                <Button
                  type="button"
                  onClick={() => {
                    void handleSubmit();
                  }}
                  disabled={!isValid || isSaving}
                >
                  {isSaving ? (
                    <>
                      <Loader2 className="mr-2 size-4 animate-spin" />
                      {t("common.saving")}
                    </>
                  ) : (
                    <>
                      {mode === "create" ? (
                        <Plus className="mr-2 size-4" />
                      ) : (
                        <Save className="mr-2 size-4" />
                      )}
                      {mode === "create" ? t("common.create") : t("common.save")}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="capabilities" className="space-y-4">
            {isLoadingCapabilities ? (
              <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-border/60 text-sm text-muted-foreground">
                <Loader2 className="mr-2 size-4 animate-spin" />
                {t("library.presetsPage.loadingCapabilities")}
              </div>
            ) : (
              <div className="grid gap-4 2xl:grid-cols-3">
                <CapabilitySelector
                  title={t("cardNav.skills")}
                  description={t("library.presetsPage.selectors.skills")}
                  items={capabilityItems.skills}
                  selectedIds={skillIds}
                  onChange={setSkillIds}
                  searchPlaceholder={t("library.skillsPage.searchPlaceholder")}
                  emptyLabel={t("library.presetsPage.emptySkills")}
                />
                <CapabilitySelector
                  title={t("cardNav.mcp")}
                  description={t("library.presetsPage.selectors.mcp")}
                  items={capabilityItems.mcp}
                  selectedIds={mcpServerIds}
                  onChange={setMcpServerIds}
                  searchPlaceholder={t("library.mcpLibrary.searchPlaceholder")}
                  emptyLabel={t("library.presetsPage.emptyMcp")}
                />
                <CapabilitySelector
                  title={t("cardNav.plugins")}
                  description={t("library.presetsPage.selectors.plugins")}
                  items={capabilityItems.plugins}
                  selectedIds={pluginIds}
                  onChange={setPluginIds}
                  searchPlaceholder={t(
                    "library.pluginsPage.searchPlaceholder",
                  )}
                  emptyLabel={t("library.presetsPage.emptyPlugins")}
                />
              </div>
            )}
          </TabsContent>

          <TabsContent value="subagents" className="space-y-4">
            <div className="flex items-center justify-between gap-4 rounded-2xl border border-border/60 bg-background/40 p-4">
              <div>
                <p className="text-sm font-medium text-foreground">
                  {t("library.presetsPage.subagents.title")}
                </p>
                <p className="text-xs text-muted-foreground">
                  {t("library.presetsPage.subagents.description")}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() =>
                  setSubagentConfigs((prev) => [
                    ...prev,
                    {
                      name: "",
                      description: "",
                      prompt: "",
                      model: "inherit",
                      tools: null,
                    },
                  ])
                }
              >
                <Plus className="mr-2 size-4" />
                {t("library.presetsPage.subagents.add")}
              </Button>
            </div>

            {subagentConfigs.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-border/60 px-4 py-8 text-center text-sm text-muted-foreground">
                {t("library.presetsPage.subagents.empty")}
              </div>
            ) : (
              <div className="space-y-4">
                {subagentConfigs.map((config, index) => (
                  <div
                    key={`${index}-${config.name}`}
                    className="space-y-4 rounded-2xl border border-border/60 bg-background/40 p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-foreground">
                        {t("library.presetsPage.subagents.itemTitle", {
                          index: index + 1,
                        })}
                      </p>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setSubagentConfigs((prev) =>
                            prev.filter(
                              (_, itemIndex) => itemIndex !== index,
                            ),
                          )
                        }
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="space-y-2">
                        <Label>
                          {t("library.presetsPage.subagents.fields.name")}
                        </Label>
                        <Input
                          value={config.name}
                          onChange={(event) =>
                            setSubagentConfigs((prev) =>
                              prev.map((item, itemIndex) =>
                                itemIndex === index
                                  ? { ...item, name: event.target.value }
                                  : item,
                              ),
                            )
                          }
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>
                          {t("library.presetsPage.subagents.fields.model")}
                        </Label>
                        <select
                          value={config.model ?? "inherit"}
                          onChange={(event) =>
                            setSubagentConfigs((prev) =>
                              prev.map((item, itemIndex) =>
                                itemIndex === index
                                  ? {
                                      ...item,
                                      model: event.target
                                        .value as PresetSubAgentConfig["model"],
                                    }
                                  : item,
                              ),
                            )
                          }
                          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-xs outline-none"
                        >
                          {SUBAGENT_MODELS.map((model) => (
                            <option key={model} value={model}>
                              {model}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label>
                        {t("library.presetsPage.subagents.fields.description")}
                      </Label>
                      <Input
                        value={config.description ?? ""}
                        onChange={(event) =>
                          setSubagentConfigs((prev) =>
                            prev.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, description: event.target.value }
                                : item,
                            ),
                          )
                        }
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>
                        {t("library.presetsPage.subagents.fields.tools")}
                      </Label>
                      <Input
                        value={config.tools?.join(", ") ?? ""}
                        onChange={(event) =>
                          setSubagentConfigs((prev) =>
                            prev.map((item, itemIndex) =>
                              itemIndex === index
                                ? {
                                    ...item,
                                    tools: parseTools(event.target.value),
                                  }
                                : item,
                            ),
                          )
                        }
                        placeholder={t(
                          "library.presetsPage.subagents.fields.toolsPlaceholder",
                        )}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label>
                        {t("library.presetsPage.subagents.fields.prompt")}
                      </Label>
                      <Textarea
                        value={config.prompt ?? ""}
                        onChange={(event) =>
                          setSubagentConfigs((prev) =>
                            prev.map((item, itemIndex) =>
                              itemIndex === index
                                ? { ...item, prompt: event.target.value }
                                : item,
                            ),
                          )
                        }
                        rows={5}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </section>
    <Dialog open={visualDialogOpen} onOpenChange={setVisualDialogOpen}>
      <DialogContent className="max-w-3xl" ariaTitle={t("library.presetsPage.form.visual")}>
        <DialogHeader>
          <DialogTitle>
            {t(
              "library.presetsPage.panel.changeVisual",
              "Change preset avatar",
            )}
          </DialogTitle>
          <DialogDescription>
            {t(
              "library.presetsPage.panel.visualHint",
              "This avatar appears in the preset list and related entry points.",
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="max-h-[60vh] overflow-y-auto">
          {isLoadingVisualOptions ? (
            <div className="flex min-h-40 items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 size-4 animate-spin" />
              {t("common.loading")}
            </div>
          ) : (
            <div className="grid grid-cols-4 gap-3">
              {visualOptions.map((option) => {
                const selected = option.key === draftVisualKey;
                return (
                  <button
                    key={option.key}
                    type="button"
                    onClick={() => setDraftVisualKey(option.key)}
                    aria-pressed={selected}
                    className={
                      selected
                        ? "flex aspect-square items-center justify-center rounded-2xl border border-primary/30 bg-primary/10 p-3 shadow-sm transition-colors"
                        : "flex aspect-square items-center justify-center rounded-2xl border border-border/60 bg-card p-3 transition-colors hover:border-border hover:bg-accent/40"
                    }
                  >
                    {option.url ? (
                      <Image
                        src={option.url}
                        alt=""
                        width={52}
                        height={52}
                        unoptimized
                        className="size-12 object-contain object-center"
                      />
                    ) : (
                      <span className="text-xs font-semibold tracking-[0.18em] text-muted-foreground">
                        {option.key}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setVisualDialogOpen(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button type="button" onClick={handleVisualApply}>
            {t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  );
}
