"use client";

import * as React from "react";
import { Loader2, Plus, Save } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentMode,
  SubAgentUpdateInput,
} from "@/features/capabilities/sub-agents/types";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";

export type SubAgentDialogMode = "create" | "edit";

interface SubAgentDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: SubAgentDialogMode;
  initialAgent?: SubAgent | null;
  isSaving?: boolean;
  onCreate: (input: SubAgentCreateInput) => Promise<SubAgent | null>;
  onUpdate: (
    subAgentId: number,
    input: SubAgentUpdateInput,
  ) => Promise<SubAgent | null>;
}

function parseTools(raw: string): string[] | null {
  const list = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return list.length > 0 ? list : null;
}

export function SubAgentDialog({
  open,
  onOpenChange,
  mode,
  initialAgent,
  isSaving = false,
  onCreate,
  onUpdate,
}: SubAgentDialogProps) {
  const { t } = useT("translation");

  const [name, setName] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [agentMode, setAgentMode] = React.useState<SubAgentMode>("structured");

  const [description, setDescription] = React.useState("");
  const [tools, setTools] = React.useState("");
  const [prompt, setPrompt] = React.useState("");
  const [rawMarkdown, setRawMarkdown] = React.useState("");

  React.useEffect(() => {
    if (!open) return;

    if (mode === "edit" && initialAgent) {
      setName(initialAgent.name || "");
      setEnabled(Boolean(initialAgent.enabled));
      setAgentMode(initialAgent.mode || "structured");
      setDescription(initialAgent.description || "");
      setTools(
        Array.isArray(initialAgent.tools) ? initialAgent.tools.join(", ") : "",
      );
      setPrompt(initialAgent.prompt || "");
      setRawMarkdown(initialAgent.raw_markdown || "");
      return;
    }

    setName("");
    setEnabled(true);
    setAgentMode("structured");
    setDescription("");
    setTools("");
    setPrompt("");
    setRawMarkdown("");
  }, [open, mode, initialAgent]);

  const title =
    mode === "create"
      ? t("library.subAgents.dialog.createTitle")
      : t("library.subAgents.dialog.editTitle");

  const isValid =
    Boolean(name.trim()) &&
    (agentMode === "raw"
      ? Boolean(rawMarkdown.trim())
      : Boolean(description.trim()) && Boolean(prompt.trim()));
  const formId = "sub-agent-dialog-form";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedName = name.trim();
    if (!trimmedName) return;

    const toolsValue = parseTools(tools);

    if (mode === "create") {
      await onCreate({
        name: trimmedName,
        enabled,
        mode: agentMode,
        ...(agentMode === "raw"
          ? {
              description: description.trim() ? description.trim() : null,
              raw_markdown: rawMarkdown,
            }
          : {
              description: description,
              prompt,
              tools: toolsValue,
            }),
      });
      onOpenChange(false);
      return;
    }

    if (!initialAgent) return;
    await onUpdate(initialAgent.id, {
      name: trimmedName,
      enabled,
      mode: agentMode,
      ...(agentMode === "raw"
        ? {
            description: description.trim() ? description.trim() : null,
            raw_markdown: rawMarkdown,
          }
        : {
            description,
            prompt,
            tools: toolsValue,
          }),
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <CapabilityDialogContent
        title={title}
        maxWidth="35rem"
        maxHeight="85dvh"
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
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="subagent-name">
                  {t("library.subAgents.fields.name")}
                </Label>
                <Input
                  id="subagent-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t("library.subAgents.fields.namePlaceholder")}
                  disabled={isSaving}
                  className="font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label>{t("library.subAgents.fields.enabled")}</Label>
                <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                  <Switch
                    checked={enabled}
                    onCheckedChange={setEnabled}
                    disabled={isSaving}
                  />
                  <span className="text-sm text-muted-foreground">
                    {enabled ? t("common.enabled") : t("common.disabled")}
                  </span>
                </div>
              </div>
            </div>

            <Tabs
              value={agentMode}
              onValueChange={(v) => setAgentMode(v as SubAgentMode)}
            >
              <TabsList>
                <TabsTrigger value="structured">
                  {t("library.subAgents.mode.structured")}
                </TabsTrigger>
                <TabsTrigger value="raw">
                  {t("library.subAgents.mode.raw")}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="structured">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="subagent-description">
                      {t("library.subAgents.fields.description")}
                    </Label>
                    <Input
                      id="subagent-description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder={t(
                        "library.subAgents.fields.descriptionPlaceholder",
                      )}
                      disabled={isSaving}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="subagent-tools">
                      {t("library.subAgents.fields.tools")}
                    </Label>
                    <Input
                      id="subagent-tools"
                      value={tools}
                      onChange={(e) => setTools(e.target.value)}
                      placeholder={t(
                        "library.subAgents.fields.toolsPlaceholder",
                      )}
                      disabled={isSaving}
                      className="font-mono"
                    />
                    <p className="text-xs text-muted-foreground">
                      {t("library.subAgents.fields.toolsHint")}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="subagent-prompt">
                      {t("library.subAgents.fields.prompt")}
                    </Label>
                    <Textarea
                      id="subagent-prompt"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder={t(
                        "library.subAgents.fields.promptPlaceholder",
                      )}
                      disabled={isSaving}
                      className="min-h-[220px]"
                    />
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="raw">
                <div className="space-y-2">
                  <Label htmlFor="subagent-raw">
                    {t("library.subAgents.fields.rawMarkdown")}
                  </Label>
                  <Textarea
                    id="subagent-raw"
                    value={rawMarkdown}
                    onChange={(e) => setRawMarkdown(e.target.value)}
                    placeholder={t(
                      "library.subAgents.fields.rawMarkdownPlaceholder",
                    )}
                    disabled={isSaving}
                    className="min-h-[260px] font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("library.subAgents.fields.rawMarkdownHint")}
                  </p>

                  <div className="space-y-2 pt-2">
                    <Label htmlFor="subagent-raw-description">
                      {t("library.subAgents.fields.descriptionOptional")}
                    </Label>
                    <Input
                      id="subagent-raw-description"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder={t(
                        "library.subAgents.fields.descriptionPlaceholder",
                      )}
                      disabled={isSaving}
                    />
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </form>
      </CapabilityDialogContent>
    </Dialog>
  );
}
