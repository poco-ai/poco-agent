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
  SlashCommand,
  SlashCommandCreateInput,
  SlashCommandMode,
  SlashCommandUpdateInput,
} from "@/features/capabilities/slash-commands/types";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";

export type SlashCommandDialogMode = "create" | "edit";

interface SlashCommandDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: SlashCommandDialogMode;
  initialCommand?: SlashCommand | null;
  isSaving?: boolean;
  onCreate: (input: SlashCommandCreateInput) => Promise<SlashCommand | null>;
  onUpdate: (
    commandId: number,
    input: SlashCommandUpdateInput,
  ) => Promise<SlashCommand | null>;
}

export function SlashCommandDialog({
  open,
  onOpenChange,
  mode,
  initialCommand,
  isSaving = false,
  onCreate,
  onUpdate,
}: SlashCommandDialogProps) {
  const { t } = useT("translation");

  const [name, setName] = React.useState("");
  const [enabled, setEnabled] = React.useState(true);
  const [commandMode, setCommandMode] = React.useState<SlashCommandMode>("raw");

  const [description, setDescription] = React.useState("");
  const [argumentHint, setArgumentHint] = React.useState("");
  const [allowedTools, setAllowedTools] = React.useState("");

  const [content, setContent] = React.useState("");
  const [rawMarkdown, setRawMarkdown] = React.useState("");

  React.useEffect(() => {
    if (!open) return;

    if (mode === "edit" && initialCommand) {
      setName(initialCommand.name || "");
      setEnabled(Boolean(initialCommand.enabled));
      setCommandMode(initialCommand.mode || "raw");
      setDescription(initialCommand.description || "");
      setArgumentHint(initialCommand.argument_hint || "");
      setAllowedTools(initialCommand.allowed_tools || "");
      setContent(initialCommand.content || "");
      setRawMarkdown(initialCommand.raw_markdown || "");
      return;
    }

    setName("");
    setEnabled(true);
    setCommandMode("raw");
    setDescription("");
    setArgumentHint("");
    setAllowedTools("");
    setContent("");
    setRawMarkdown("");
  }, [open, mode, initialCommand]);

  const title =
    mode === "create"
      ? t("library.slashCommands.dialog.createTitle")
      : t("library.slashCommands.dialog.editTitle");

  const isValid =
    Boolean(name.trim()) &&
    (commandMode === "raw"
      ? Boolean(rawMarkdown.trim())
      : Boolean(content.trim()));
  const formId = "slash-command-dialog-form";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedName = name.trim();
    if (!trimmedName) return;

    const base = {
      name: trimmedName,
      enabled,
      mode: commandMode,
      description,
      argument_hint: argumentHint,
      allowed_tools: allowedTools,
    } as const;

    if (mode === "create") {
      await onCreate({
        ...base,
        ...(commandMode === "raw"
          ? { raw_markdown: rawMarkdown }
          : { content }),
      });
      onOpenChange(false);
      return;
    }

    if (!initialCommand) return;
    await onUpdate(initialCommand.id, {
      ...base,
      ...(commandMode === "raw" ? { raw_markdown: rawMarkdown } : { content }),
    });
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <CapabilityDialogContent
        title={title}
        maxWidth="35rem"
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
                <Label htmlFor="slash-command-name">
                  {t("library.slashCommands.fields.name")}{" "}
                  <span className="text-muted-foreground font-normal">
                    ({t("library.slashCommands.fields.nameHint")})
                  </span>
                </Label>
                <Input
                  id="slash-command-name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder={t(
                    "library.slashCommands.fields.namePlaceholder",
                  )}
                  disabled={isSaving}
                  className="font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label>{t("library.slashCommands.fields.enabled")}</Label>
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
              value={commandMode}
              onValueChange={(v) => setCommandMode(v as SlashCommandMode)}
            >
              <TabsList>
                <TabsTrigger value="raw">
                  {t("library.slashCommands.mode.raw")}
                </TabsTrigger>
                <TabsTrigger value="structured">
                  {t("library.slashCommands.mode.structured")}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="raw">
                <div className="space-y-2">
                  <Label htmlFor="slash-command-raw">
                    {t("library.slashCommands.fields.rawMarkdown")}
                  </Label>
                  <Textarea
                    id="slash-command-raw"
                    value={rawMarkdown}
                    onChange={(e) => setRawMarkdown(e.target.value)}
                    placeholder={t(
                      "library.slashCommands.fields.rawMarkdownPlaceholder",
                    )}
                    disabled={isSaving}
                    className="min-h-[220px] font-mono"
                  />
                  <p className="text-xs text-muted-foreground">
                    {t("library.slashCommands.fields.modelIgnoredHint")}
                  </p>
                </div>
              </TabsContent>

              <TabsContent value="structured">
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="slash-command-description">
                        {t("library.slashCommands.fields.description")}
                      </Label>
                      <Input
                        id="slash-command-description"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        placeholder={t(
                          "library.slashCommands.fields.descriptionPlaceholder",
                        )}
                        disabled={isSaving}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="slash-command-argument-hint">
                        {t("library.slashCommands.fields.argumentHint")}
                      </Label>
                      <Input
                        id="slash-command-argument-hint"
                        value={argumentHint}
                        onChange={(e) => setArgumentHint(e.target.value)}
                        placeholder={t(
                          "library.slashCommands.fields.argumentHintPlaceholder",
                        )}
                        disabled={isSaving}
                        className="font-mono"
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="slash-command-allowed-tools">
                      {t("library.slashCommands.fields.allowedTools")}
                    </Label>
                    <Input
                      id="slash-command-allowed-tools"
                      value={allowedTools}
                      onChange={(e) => setAllowedTools(e.target.value)}
                      placeholder={t(
                        "library.slashCommands.fields.allowedToolsPlaceholder",
                      )}
                      disabled={isSaving}
                      className="font-mono"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="slash-command-content">
                      {t("library.slashCommands.fields.content")}
                    </Label>
                    <Textarea
                      id="slash-command-content"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      placeholder={t(
                        "library.slashCommands.fields.contentPlaceholder",
                      )}
                      disabled={isSaving}
                      className="min-h-[220px]"
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
