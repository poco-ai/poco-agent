"use client";

import * as React from "react";
import Image from "next/image";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";
import { ArrowDownToLine } from "lucide-react";
import { Bot, Info, Sparkles } from "lucide-react";
import { toast } from "sonner";

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
import { HeaderSearchInput } from "@/components/shared/header-search-input";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import { CapabilitySelector } from "@/features/capabilities/presets/components/capability-selector";
import { PresetGlyph } from "@/features/capabilities/presets/components/preset-glyph";
import { subAgentsService } from "@/features/capabilities/sub-agents/api/sub-agents-api";
import { SubAgentDialog } from "@/features/capabilities/sub-agents/components/sub-agent-dialog";
import { SubAgentListItem } from "@/features/capabilities/sub-agents/components/sub-agent-list-item";
import type {
  SubAgent,
  SubAgentCreateInput,
} from "@/features/capabilities/sub-agents/types";
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
import { ApiError } from "@/lib/errors";
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

function normalizeSubagentConfig(
  value?: PresetSubAgentConfig[],
): PresetSubAgentConfig[] {
  return value?.map((item) => ({ ...item, tools: item.tools ?? null })) ?? [];
}

function toPresetSubAgentConfig(
  subAgent: Pick<SubAgent, "mode" | "name" | "description" | "prompt" | "tools">,
): PresetSubAgentConfig | null {
  if (subAgent.mode !== "structured") {
    return null;
  }

  const prompt = (subAgent.prompt || "").trim();
  const description = (subAgent.description || "").trim();
  if (!description || !prompt) {
    return null;
  }

  return {
    name: subAgent.name,
    description,
    prompt,
    model: null,
    tools: subAgent.tools ?? null,
  };
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
  const [availableSubAgents, setAvailableSubAgents] = React.useState<SubAgent[]>(
    [],
  );
  const [isLoadingCapabilities, setIsLoadingCapabilities] =
    React.useState(false);
  const [isLoadingVisualOptions, setIsLoadingVisualOptions] =
    React.useState(false);
  const [isLoadingImportSubAgents, setIsLoadingImportSubAgents] =
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
  const [subAgentDialogOpen, setSubAgentDialogOpen] = React.useState(false);
  const [importDialogOpen, setImportDialogOpen] = React.useState(false);
  const [importSearchQuery, setImportSearchQuery] = React.useState("");
  const [selectedImportSubAgentId, setSelectedImportSubAgentId] = React.useState<
    number | null
  >(null);
  const [draftVisualKey, setDraftVisualKey] = React.useState(
    getPresetFormInitialVisualKey(),
  );
  const [isCreatingSubAgent, setIsCreatingSubAgent] = React.useState(false);

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
      setIsLoadingImportSubAgents(true);
      try {
        const [skills, servers, plugins, visuals, subAgents] = await Promise.all([
          skillsService.listSkills({ revalidate: 0 }),
          mcpService.listServers({ revalidate: 0 }),
          pluginsService.listPlugins({ revalidate: 0 }),
          presetsService.listPresetVisuals({ revalidate: 0 }),
          subAgentsService.list({ revalidate: 0 }),
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
        setAvailableSubAgents(subAgents);
      } catch (error) {
        console.error(
          "[PresetEditorPanel] Failed to load preset panel data",
          error,
        );
      } finally {
        if (active) {
          setIsLoadingCapabilities(false);
          setIsLoadingVisualOptions(false);
          setIsLoadingImportSubAgents(false);
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

  const importableSubAgents = React.useMemo(() => {
    const importedNameSet = new Set(
      subagentConfigs.map((config) => config.name.trim()).filter(Boolean),
    );
    const normalizedQuery = importSearchQuery.trim().toLowerCase();

    return availableSubAgents.filter((agent) => {
      if (agent.mode !== "structured") return false;
      if (importedNameSet.has(agent.name.trim())) return false;

      if (!normalizedQuery) return true;
      return (
        agent.name.toLowerCase().includes(normalizedQuery) ||
        (agent.description || "").toLowerCase().includes(normalizedQuery) ||
        (agent.prompt || "").toLowerCase().includes(normalizedQuery)
      );
    });
  }, [availableSubAgents, importSearchQuery, subagentConfigs]);

  React.useEffect(() => {
    if (!importDialogOpen) return;
    setSelectedImportSubAgentId(importableSubAgents[0]?.id ?? null);
  }, [importDialogOpen, importableSubAgents]);

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

  const handleCreateSubAgent = React.useCallback(
    async (input: SubAgentCreateInput) => {
      setIsCreatingSubAgent(true);
      try {
        const created = await subAgentsService.create(input);
        setAvailableSubAgents((prev) => [created, ...prev]);

        const presetConfig = toPresetSubAgentConfig(created);
        if (presetConfig) {
          setSubagentConfigs((prev) => [...prev, presetConfig]);
        }

        toast.success(t("library.subAgents.toasts.created"));
        return created;
      } catch (error) {
        console.error("[PresetEditorPanel] create subagent failed:", error);
        toast.error(
          error instanceof ApiError && error.message.trim()
            ? error.message
            : t("library.subAgents.toasts.error"),
        );
        return null;
      } finally {
        setIsCreatingSubAgent(false);
      }
    },
    [t],
  );

  const handleImportSelectedSubAgent = React.useCallback(() => {
    if (selectedImportSubAgentId === null) return;
    const selectedSubAgent = availableSubAgents.find(
      (agent) => agent.id === selectedImportSubAgentId,
    );
    if (!selectedSubAgent) return;

    const presetConfig = toPresetSubAgentConfig(selectedSubAgent);
    if (!presetConfig) {
      toast.error(t("library.subAgents.toasts.error"));
      return;
    }

    setSubagentConfigs((prev) => [...prev, presetConfig]);
    setSelectedImportSubAgentId(null);
    setImportSearchQuery("");
    setImportDialogOpen(false);
  }, [availableSubAgents, selectedImportSubAgentId, t]);

  return (
    <>
      <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col">
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
              <TabsList className="w-full justify-start gap-2 overflow-x-auto bg-transparent p-0">
                <TabsTrigger
                  value="general"
                  className="max-w-32 flex-1 gap-1.5 rounded-md border border-border/60 bg-muted/60 data-[state=active]:border-transparent data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Info className="size-4 shrink-0" />
                  {t("library.presetsPage.tabs.general")}
                </TabsTrigger>
                <TabsTrigger
                  value="capabilities"
                  className="max-w-32 flex-1 gap-1.5 rounded-md border border-border/60 bg-muted/60 data-[state=active]:border-transparent data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Sparkles className="size-4 shrink-0" />
                  {t("library.presetsPage.tabs.capabilities")}
                </TabsTrigger>
                <TabsTrigger
                  value="subagents"
                  className="max-w-32 flex-1 gap-1.5 rounded-md border border-border/60 bg-muted/60 data-[state=active]:border-transparent data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                >
                  <Bot className="size-4 shrink-0" />
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
              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setSubAgentDialogOpen(true)}
                >
                  <Plus className="mr-2 size-4" />
                  {t("common.add")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setImportDialogOpen(true)}
                >
                  <ArrowDownToLine className="mr-2 size-4" />
                  {t(
                    "library.presetsPage.subagents.import",
                    "导入",
                  )}
                </Button>
              </div>
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
                    className="space-y-3"
                  >
                    <SubAgentListItem
                      name={config.name}
                      description={config.description}
                      tools={config.tools}
                      mode="structured"
                      trailing={
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
                      }
                    />
                  </div>
                ))}
              </div>
            )}
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </section>
    <SubAgentDialog
      open={subAgentDialogOpen}
      onOpenChange={setSubAgentDialogOpen}
      mode="create"
      isSaving={isCreatingSubAgent}
      nameHint={t(
        "library.subAgents.fields.nameHint",
        "Only A-Za-z0-9._- are allowed.",
      )}
      onCreate={handleCreateSubAgent}
      onUpdate={async () => null}
    />
    <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
      <DialogContent className="max-w-3xl" ariaTitle={t("library.presetsPage.subagents.import", "导入")}>
        <DialogHeader>
          <DialogTitle>
            {t(
              "library.presetsPage.subagents.importDialogTitle",
              "导入已有子代理",
            )}
          </DialogTitle>
          <DialogDescription>
            {t(
              "library.presetsPage.subagents.importDialogDescription",
              "从能力模块中已配置的结构化子代理里选择，并复制到当前预设。",
            )}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <HeaderSearchInput
            value={importSearchQuery}
            onChange={setImportSearchQuery}
            placeholder={t("library.subAgents.searchPlaceholder")}
            className="w-full"
          />
          <div className="max-h-[60vh] space-y-3 overflow-y-auto">
            {isLoadingImportSubAgents ? (
              <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
                <Loader2 className="mr-2 size-4 animate-spin" />
                {t("common.loading")}
              </div>
            ) : importableSubAgents.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border/60 px-4 py-6 text-center text-sm text-muted-foreground">
                {t(
                  "library.presetsPage.subagents.importEmpty",
                  "暂无可导入的结构化子代理。",
                )}
              </div>
            ) : (
              importableSubAgents.map((agent) => (
                <SubAgentListItem
                  key={agent.id}
                  name={agent.name}
                  description={agent.description}
                  tools={agent.tools}
                  mode={agent.mode}
                  source={agent.source}
                  enabled={agent.enabled}
                  selected={agent.id === selectedImportSubAgentId}
                  onClick={() => setSelectedImportSubAgentId(agent.id)}
                />
              ))
            )}
          </div>
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => setImportDialogOpen(false)}
          >
            {t("common.cancel")}
          </Button>
          <Button
            type="button"
            onClick={handleImportSelectedSubAgent}
            disabled={selectedImportSubAgentId === null}
          >
            {t("common.import", "导入")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
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
