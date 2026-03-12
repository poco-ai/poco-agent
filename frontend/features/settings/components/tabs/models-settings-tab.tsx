"use client";

import { Switch } from "@/components/ui/switch";
import { useT } from "@/lib/i18n/client";

interface ModelsSettingsTabProps {
  isGlmEnabled: boolean;
  onToggleGlm: (checked: boolean) => void;
}

export function ModelsSettingsTab({
  isGlmEnabled,
  onToggleGlm,
}: ModelsSettingsTabProps) {
  const { t } = useT("translation");

  return (
    <div className="flex-1 space-y-8 overflow-y-auto p-6">
      <section className="space-y-3">
        <h3 className="text-sm font-medium text-foreground">
          {t("settings.modelConfigTitle")}
        </h3>
        <div className="flex items-center justify-between gap-4 py-2">
          <p className="text-sm font-medium text-foreground">
            {t("settings.modelGlm")}
          </p>
          <Switch checked={isGlmEnabled} onCheckedChange={onToggleGlm} />
        </div>
      </section>
    </div>
  );
}
