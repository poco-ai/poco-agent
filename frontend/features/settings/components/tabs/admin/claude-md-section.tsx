import * as React from "react";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/client";
import type { CustomInstructionsSettings } from "@/features/capabilities/personalization/types";

import { AdminSectionError, AdminSectionLoading, SectionCard } from "./shared";

interface AdminClaudeMdSectionProps {
  settings: CustomInstructionsSettings | null;
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onSave: (input: { enabled: boolean; content: string }) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function AdminClaudeMdSection({
  settings,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onSave,
  onDelete,
}: AdminClaudeMdSectionProps) {
  const { t } = useT("translation");
  const [enabled, setEnabled] = React.useState(false);
  const [content, setContent] = React.useState("");

  React.useEffect(() => {
    setEnabled(Boolean(settings?.enabled));
    setContent(settings?.content || "");
  }, [settings]);

  return (
    <SectionCard
      title={t("settings.admin.claudeMdTitle")}
      description={t("settings.admin.claudeMdDescription")}
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
          <Switch checked={enabled} onCheckedChange={setEnabled} />
          <span className="text-sm text-muted-foreground">
            {enabled ? t("common.enabled") : t("common.disabled")}
          </span>
        </div>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="min-h-40 font-mono text-sm"
          placeholder={t(
            "library.personalization.customInstructions.editor.template",
          )}
        />
        <div className="flex justify-end gap-2">
          <Button
            variant="outline"
            onClick={() => void onDelete()}
            disabled={isSaving}
          >
            {t("library.personalization.header.clear")}
          </Button>
          <Button
            onClick={() => void onSave({ enabled, content })}
            disabled={isSaving}
          >
            {t("settings.admin.save")}
          </Button>
        </div>
      </div>
    </SectionCard>
  );
}
