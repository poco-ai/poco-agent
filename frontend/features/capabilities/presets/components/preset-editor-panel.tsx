"use client";

import * as React from "react";
import Image from "next/image";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

  const title =
    mode === "create"
      ? t("library.presetsPage.dialog.createTitle")
      : t("library.presetsPage.dialog.editTitle");
  const subtitle =
    mode === "create"
      ? t(
          "library.presetsPage.panel.createDescription",
          "Build a reusable preset with default capabilities and instructions.",
        )
      : t(
          "library.presetsPage.panel.editDescription",
          "Review and adjust this preset without leaving the library.",
        );

  const detailPreset = preset ?? {
    name: name || t("library.presetsPage.panel.newPresetLabel", "New preset"),
    visual_key: visualKey,
    visual_url: selectedVisualOption?.url ?? null,
  };

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="border-b border-border/50 px-6 pb-5 pt-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-4">
            <PresetGlyph preset={detailPreset} variant="card" />
            <div className="min-w-0 space-y-2">
              <div className="space-y-1">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  {t("library.presetsPage.panel.detailLabel", "Preset detail")}
                </p>
                <h2 className="text-xl font-semibold text-foreground">
                  {title}
                </h2>
              </div>
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground">
                {subtitle}
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">
                  {t("library.presetsPage.tabs.capabilities")}{" "}
                  {skillIds.length + mcpServerIds.length + pluginIds.length}
                </Badge>
                {browserEnabled ? (
                  <Badge variant="outline">
                    {t("library.presetsPage.flags.browser")}
                  </Badge>
                ) : null}
                {memoryEnabled ? (
                  <Badge variant="outline">
                    {t("library.presetsPage.flags.memory")}
                  </Badge>
                ) : null}
                {subagentConfigs.length > 0 ? (
                  <Badge variant="outline">
                    {t("library.presetsPage.tabs.subagents")}{" "}
                    {subagentConfigs.length}
                  </Badge>
                ) : null}
              </div>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2">
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

        {mode === "edit" && preset ? (
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-border/50 bg-background/40 px-4 py-3">
              <div className="text-xs text-muted-foreground">
                {t("library.presetsPage.panel.scopeLabel", "Scope")}
              </div>
              <div className="mt-1 text-sm font-medium text-foreground">
                {preset.scope ?? t("library.presetsPage.panel.scopeFallback", "Personal")}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 bg-background/40 px-4 py-3">
              <div className="text-xs text-muted-foreground">
                {t("library.presetsPage.panel.visualLabel", "Avatar")}
              </div>
              <div className="mt-1 truncate text-sm font-medium text-foreground">
                {selectedVisualOption?.name ||
                  selectedVisualOption?.key ||
                  preset.visual_name ||
                  preset.visual_key}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 bg-background/40 px-4 py-3">
              <div className="text-xs text-muted-foreground">
                {t("library.presetsPage.panel.createdLabel", "Created")}
              </div>
              <div className="mt-1 text-sm font-medium text-foreground">
                {formatTimestamp(preset.created_at) ?? "—"}
              </div>
            </div>
            <div className="rounded-2xl border border-border/50 bg-background/40 px-4 py-3">
              <div className="text-xs text-muted-foreground">
                {t("library.presetsPage.panel.updatedLabel", "Updated")}
              </div>
              <div className="mt-1 text-sm font-medium text-foreground">
                {formatTimestamp(preset.updated_at) ?? "—"}
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5">
        <Tabs defaultValue="general" className="flex flex-col gap-5">
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
            <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
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
              </div>

              <div className="space-y-5">
                <div className="space-y-2">
                  <Label>{t("library.presetsPage.form.visual")}</Label>
                  <div className="rounded-2xl border border-border/60 bg-background/40 p-4">
                    <div className="mb-4 flex items-center gap-3 rounded-2xl border border-border/60 bg-background/70 p-3">
                      <div className="flex size-14 items-center justify-center rounded-2xl border border-border/60 bg-muted/30">
                        {selectedVisualOption?.url ? (
                          <Image
                            src={selectedVisualOption.url}
                            alt=""
                            width={40}
                            height={40}
                            unoptimized
                            className="size-10 object-contain object-center"
                          />
                        ) : (
                          <span className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">
                            {selectedVisualOption?.key ?? visualKey}
                          </span>
                        )}
                      </div>
                      <div className="min-w-0">
                        <div className="truncate text-sm font-medium text-foreground">
                          {selectedVisualOption?.name ||
                            selectedVisualOption?.key ||
                            visualKey}
                        </div>
                        <div className="truncate text-xs text-muted-foreground">
                          {t(
                            "library.presetsPage.panel.visualHint",
                            "This avatar appears in the preset list and related entry points.",
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="max-h-[20rem] overflow-y-auto">
                      {isLoadingVisualOptions ? (
                        <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
                          <Loader2 className="mr-2 size-4 animate-spin" />
                          {t("common.loading")}
                        </div>
                      ) : (
                        <div className="grid grid-cols-4 gap-3">
                          {visualOptions.map((option) => {
                            const selected = option.key === visualKey;
                            return (
                              <button
                                key={option.key}
                                type="button"
                                onClick={() => setVisualKey(option.key)}
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
                  </div>
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
  );
}
