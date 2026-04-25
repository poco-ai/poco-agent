import * as React from "react";
import { Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ModelConfigResponse } from "@/features/settings/types";
import { useT } from "@/lib/i18n/client";

import { AdminSectionError, AdminSectionLoading, SectionCard } from "./shared";

interface AdminModelConfigSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  modelConfig: ModelConfigResponse | null;
  onRetry: () => void;
  onSave: (input: {
    default_model: string;
    model_list: string[];
  }) => Promise<void>;
}

export function AdminModelConfigSection({
  isLoading,
  hasError,
  isSaving,
  modelConfig,
  onRetry,
  onSave,
}: AdminModelConfigSectionProps) {
  const { t } = useT("translation");
  const [defaultModel, setDefaultModel] = React.useState("");
  const [modelListText, setModelListText] = React.useState("");

  React.useEffect(() => {
    setDefaultModel(modelConfig?.default_model ?? "");
    setModelListText(modelConfig?.model_list.join("\n") ?? "");
  }, [modelConfig]);

  return (
    <SectionCard
      title={t("settings.admin.modelConfigTitle")}
      description={t("settings.admin.modelConfigDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="admin-default-model">DEFAULT_MODEL</Label>
            <Input
              id="admin-default-model"
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="admin-model-list">MODEL_LIST</Label>
            <Textarea
              id="admin-model-list"
              value={modelListText}
              onChange={(e) => setModelListText(e.target.value)}
              className="min-h-28"
            />
          </div>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="text-xs text-muted-foreground">
            {modelConfig?.model_list.join(", ") || "-"}
          </div>
          <Button
            onClick={() =>
              void onSave({
                default_model: defaultModel,
                model_list: modelListText
                  .split(/\n|,/)
                  .map((item) => item.trim())
                  .filter(Boolean),
              })
            }
            disabled={isSaving}
          >
            <Save className="mr-2 size-4" />
            {t("settings.admin.save")}
          </Button>
        </div>
      </div>
    </SectionCard>
  );
}
