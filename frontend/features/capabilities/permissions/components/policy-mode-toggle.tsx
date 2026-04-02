"use client";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useT } from "@/lib/i18n/client";

interface PolicyModeToggleProps {
  mode: "audit" | "enforce";
  onChange: (mode: "audit" | "enforce") => void;
}

export function PolicyModeToggle({ mode, onChange }: PolicyModeToggleProps) {
  const { t } = useT("translation");
  const isEnforce = mode === "enforce";

  return (
    <div className="flex items-center justify-between gap-4 rounded-xl border border-border/60 bg-background/60 px-4 py-3">
      <div className="space-y-0.5">
        <Label className="text-sm font-medium">
          {t("permissions.mode.label", "Enforcement Mode")}
        </Label>
        <p className="text-xs text-muted-foreground">
          {isEnforce
            ? t("permissions.mode.enforceHint", "Rules actively block or allow tool calls")
            : t("permissions.mode.auditHint", "Rules are evaluated but not enforced — decisions are logged only")}
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant={isEnforce ? "destructive" : "secondary"} className="text-xs">
          {isEnforce
            ? t("permissions.mode.enforce", "Enforce")
            : t("permissions.mode.audit", "Audit only")}
        </Badge>
        <Switch
          checked={isEnforce}
          onCheckedChange={(checked) =>
            onChange(checked ? "enforce" : "audit")
          }
        />
      </div>
    </div>
  );
}
