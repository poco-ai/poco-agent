"use client";

import * as React from "react";
import { Loader2, Plus, Save } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import type { EnvVarUpsertInput } from "@/features/capabilities/env-vars/hooks/use-env-vars-store";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";

export type EnvVarDialogMode = "create" | "edit" | "override";

interface EnvVarUpsertDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (payload: EnvVarUpsertInput) => Promise<void> | void;
  isSaving?: boolean;
  mode?: EnvVarDialogMode;
  initialKey?: string;
  initialDescription?: string | null;
  keyReadOnly?: boolean;
}

export function AddEnvVarDialog({
  open,
  onOpenChange,
  onSave,
  isSaving = false,
  mode = "create",
  initialKey,
  initialDescription,
  keyReadOnly,
}: EnvVarUpsertDialogProps) {
  const { t } = useT("translation");
  const [key, setKey] = React.useState(initialKey || "");
  const [value, setValue] = React.useState("");
  const [description, setDescription] = React.useState(
    initialDescription || "",
  );

  const isKeyReadOnly = Boolean(keyReadOnly ?? mode !== "create");
  const requiresValue = mode !== "edit";

  // Reset form when dialog opens / mode changes
  React.useEffect(() => {
    if (!open) return;
    setKey(initialKey || "");
    setValue("");
    setDescription(initialDescription || "");
  }, [open, initialDescription, initialKey]);

  const title =
    mode === "create"
      ? t("library.envVars.addTitle")
      : mode === "override"
        ? t("library.envVars.overrideTitle")
        : t("library.envVars.editTitle");

  const valueHint =
    mode === "edit"
      ? t("library.envVars.valueUpdateHint")
      : t("library.envVars.valueCreateHint");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedKey = key.trim();
    const trimmedValue = value.trim();

    if (!trimmedKey) return;
    if (requiresValue && !trimmedValue) return;

    await onSave({
      key: trimmedKey,
      value: trimmedValue ? trimmedValue : undefined,
      description: description.trim() || undefined,
    });

    onOpenChange(false);
  };

  const isValid =
    Boolean(key.trim()) && (requiresValue ? Boolean(value.trim()) : true);
  const formId = "env-var-dialog-form";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <CapabilityDialogContent
        title={title}
        size="md"
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
                  {t("library.envVars.saving")}
                </>
              ) : (
                <>
                  {mode === "create" ? (
                    <Plus className="mr-2 size-4" />
                  ) : (
                    <Save className="mr-2 size-4" />
                  )}
                  {mode === "create"
                    ? t("library.envVars.addButton")
                    : t("library.envVars.save")}
                </>
              )}
            </Button>
          </DialogFooter>
        }
      >
        <form id={formId} onSubmit={handleSubmit}>
          <div className="space-y-4">
            {/* Key */}
            <div className="space-y-2">
              <Label htmlFor="env-key">{t("library.envVars.keyLabel")}</Label>
              <Input
                id="env-key"
                value={key}
                onChange={(e) => setKey(e.target.value)}
                placeholder="ANTHROPIC_API_KEY"
                autoCapitalize="characters"
                disabled={isSaving || isKeyReadOnly}
                className="font-mono"
              />
            </div>

            {/* Value */}
            <div className="space-y-2">
              <Label htmlFor="env-value">
                {t("library.envVars.valueLabel")}
              </Label>
              <Input
                id="env-value"
                type="password"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={t("library.envVars.valuePlaceholder")}
                disabled={isSaving}
              />
              <p className="text-xs text-muted-foreground">{valueHint}</p>
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="env-description">
                {t("library.envVars.descriptionLabel")}
              </Label>
              <Input
                id="env-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={t("library.envVars.descriptionPlaceholder")}
                disabled={isSaving}
              />
            </div>

            <p className="text-xs text-muted-foreground">
              {t("library.envVars.secretHelp")}
            </p>
          </div>
        </form>
      </CapabilityDialogContent>
    </Dialog>
  );
}
