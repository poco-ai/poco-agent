"use client";

import * as React from "react";
import Image from "next/image";
import { Loader2, Plus, Save, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { presetsService } from "@/features/capabilities/presets/api/presets-api";
import { CapabilitySelector } from "@/features/capabilities/presets/components/capability-selector";
import {
  getPresetFormInitialVisualKey,
  isPresetFormValid,
} from "@/features/capabilities/presets/lib/preset-form";
import type {
  Preset,
  PresetCapabilityItem,
  PresetCreateInput,
  PresetSubAgentConfig,
  PresetVisualOption,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";
import { useT } from "@/lib/i18n/client";

export type PresetDialogMode = "create" | "edit";

interface PresetFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: PresetDialogMode;
  initialPreset?: Preset | null;
  savingKey?: string | null;
  onCreate: (input: PresetCreateInput) => Promise<Preset | null>;
  onUpdate: (
    presetId: number,
    input: PresetUpdateInput,
  ) => Promise<Preset | null>;
  onDelete?: (presetId: number) => Promise<void>;
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

export function PresetFormDialog({
  open,
  onOpenChange,
  mode,
  initialPreset,
  savingKey,
  onCreate,
  onUpdate,
  onDelete,
}: PresetFormDialogProps) {
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
    if (!open) return;

    if (mode === "edit" && initialPreset) {
      setName(initialPreset.name);
      setDescription(initialPreset.description || "");
      setVisualKey(getPresetFormInitialVisualKey(initialPreset.visual_key));
      setPromptTemplate(initialPreset.prompt_template || "");
      setBrowserEnabled(initialPreset.browser_enabled);
      setMemoryEnabled(initialPreset.memory_enabled);
      setSkillIds(initialPreset.skill_ids);
      setMcpServerIds(initialPreset.mcp_server_ids);
      setPluginIds(initialPreset.plugin_ids);
      setSubagentConfigs(
        normalizeSubagentConfig(initialPreset.subagent_configs),
      );
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
  }, [initialPreset, mode, open]);

  React.useEffect(() => {
    if (!open) return;
    let active = true;

    const loadDialogData = async () => {
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
          "[PresetFormDialog] Failed to load preset dialog data",
          error,
        );
      } finally {
        if (active) {
          setIsLoadingCapabilities(false);
          setIsLoadingVisualOptions(false);
        }
      }
    };

    void loadDialogData();
    return () => {
      active = false;
    };
  }, [open]);

  const isSaving =
    mode === "create"
      ? savingKey === "create"
      : savingKey === String(initialPreset?.preset_id);

  const isValid = isPresetFormValid({ name, visualKey });
  const formId = "preset-form-dialog";

  const handleDelete = React.useCallback(async () => {
    if (!initialPreset || !onDelete) {
      return;
    }
    await onDelete(initialPreset.preset_id);
    onOpenChange(false);
  }, [initialPreset, onDelete, onOpenChange]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!isValid) return;

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

    const result =
      mode === "create"
        ? await onCreate(payload)
        : initialPreset
          ? await onUpdate(initialPreset.preset_id, payload)
          : null;

    if (result) {
      onOpenChange(false);
    }
  };

  const title =
    mode === "create"
      ? t("library.presetsPage.dialog.createTitle")
      : t("library.presetsPage.dialog.editTitle");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <CapabilityDialogContent
        title={title}
        maxWidth="68rem"
        maxHeight="86dvh"
        desktopMaxHeight="90dvh"
        footer={
          <DialogFooter className="grid grid-cols-2 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving}
              className="w-full"
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="submit"
              form={formId}
              disabled={!isValid || isSaving}
              className="w-full"
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
          </DialogFooter>
        }
      >
        <form id={formId} onSubmit={handleSubmit}>
          <Tabs defaultValue="general" className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-3">
              <TabsList>
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
              {mode === "edit" && initialPreset && onDelete ? (
                <Button
                  type="button"
                  variant="outline"
                  disabled={isSaving}
                  onClick={() => {
                    void handleDelete();
                  }}
                  className="shrink-0 text-destructive hover:text-destructive"
                >
                  <Trash2 className="mr-2 size-4" />
                  {t("common.delete")}
                </Button>
              ) : null}
            </div>

            <TabsContent value="general" className="min-h-[30rem] space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="preset-name">
                      {t("library.presetsPage.form.name")}
                    </Label>
                    <Input
                      id="preset-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      placeholder={t(
                        "library.presetsPage.form.namePlaceholder",
                      )}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="preset-description">
                      {t("library.presetsPage.form.description")}
                    </Label>
                    <Textarea
                      id="preset-description"
                      value={description}
                      onChange={(event) => setDescription(event.target.value)}
                      placeholder={t(
                        "library.presetsPage.form.descriptionPlaceholder",
                      )}
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="preset-prompt-template">
                      {t("library.presetsPage.form.promptTemplate")}
                    </Label>
                    <Textarea
                      id="preset-prompt-template"
                      value={promptTemplate}
                      onChange={(event) =>
                        setPromptTemplate(event.target.value)
                      }
                      placeholder={t(
                        "library.presetsPage.form.promptTemplatePlaceholder",
                      )}
                      rows={6}
                    />
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>{t("library.presetsPage.form.visual")}</Label>
                    <div className="max-h-[22rem] overflow-y-auto rounded-2xl border border-border/60 bg-muted/10 p-4">
                      {isLoadingVisualOptions ? (
                        <div className="flex min-h-32 items-center justify-center text-sm text-muted-foreground">
                          <Loader2 className="mr-2 size-4 animate-spin" />
                          {t("common.loading")}
                        </div>
                      ) : (
                        <div className="grid grid-cols-5 gap-3">
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
                                    width={64}
                                    height={64}
                                    unoptimized
                                    className="size-16 object-contain object-center"
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
                  <div className="space-y-3 rounded-2xl border border-border/60 p-4">
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

            <TabsContent
              value="capabilities"
              className="min-h-[30rem] space-y-4"
            >
              {isLoadingCapabilities ? (
                <div className="flex min-h-40 items-center justify-center rounded-2xl border border-dashed border-border/60 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  {t("library.presetsPage.loadingCapabilities")}
                </div>
              ) : (
                <div className="grid gap-4 xl:grid-cols-3">
                  <CapabilitySelector
                    title={t("cardNav.skills")}
                    description={t("library.presetsPage.selectors.skills")}
                    items={capabilityItems.skills}
                    selectedIds={skillIds}
                    onChange={setSkillIds}
                    searchPlaceholder={t(
                      "library.skillsPage.searchPlaceholder",
                    )}
                    emptyLabel={t("library.presetsPage.emptySkills")}
                  />
                  <CapabilitySelector
                    title={t("cardNav.mcp")}
                    description={t("library.presetsPage.selectors.mcp")}
                    items={capabilityItems.mcp}
                    selectedIds={mcpServerIds}
                    onChange={setMcpServerIds}
                    searchPlaceholder={t(
                      "library.mcpLibrary.searchPlaceholder",
                    )}
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

            <TabsContent value="subagents" className="min-h-[30rem] space-y-4">
              <div className="flex items-center justify-between gap-4 rounded-2xl border border-border/60 p-4">
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
                      className="space-y-4 rounded-2xl border border-border/60 p-4"
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
                          {t(
                            "library.presetsPage.subagents.fields.description",
                          )}
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
        </form>
      </CapabilityDialogContent>
    </Dialog>
  );
}
