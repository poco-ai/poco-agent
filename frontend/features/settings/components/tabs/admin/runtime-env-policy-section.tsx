"use client";

import * as React from "react";

import { ShieldAlert } from "lucide-react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { useT } from "@/lib/i18n/client";
import type { RuntimeEnvPolicy } from "@/features/settings/api/admin-api";

import {
  AdminLabeledTextareaField,
  AdminSectionError,
  AdminSectionLoading,
  SectionCard,
} from "./shared";

interface RuntimeEnvPolicySectionProps {
  policy: RuntimeEnvPolicy | null;
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRefresh: () => void;
  onRetry: () => void;
  onSave: (input: {
    mode: "disabled" | "opt_in";
    allowlist_patterns: string[];
    denylist_patterns: string[];
  }) => Promise<void>;
}

function parsePatterns(raw: string): string[] {
  return raw
    .split(/[\n,]/g)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function RuntimeEnvPolicySection({
  policy,
  isLoading,
  hasError,
  isSaving,
  onRefresh,
  onRetry,
  onSave,
}: RuntimeEnvPolicySectionProps) {
  const { t } = useT("translation");
  const [mode, setMode] = React.useState<"disabled" | "opt_in">("opt_in");
  const [allowlist, setAllowlist] = React.useState("");
  const [denylist, setDenylist] = React.useState("");

  React.useEffect(() => {
    if (!policy) return;
    setMode(policy.mode);
    setAllowlist(policy.allowlist_patterns.join("\n"));
    setDenylist(policy.denylist_patterns.join("\n"));
  }, [policy]);

  return (
    <SectionCard
      title={t("settings.admin.runtimeEnvPolicyTitle")}
      description={t("settings.admin.runtimeEnvPolicyDescription")}
      actions={
        <Button variant="outline" size="sm" onClick={onRefresh}>
          {t("settings.admin.refresh")}
        </Button>
      }
    >
      {isLoading ? <AdminSectionLoading /> : null}
      {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
      <div
        className={
          isLoading || hasError ? "pointer-events-none opacity-60" : undefined
        }
      >
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 text-sm text-muted-foreground">
          <div className="mb-2 flex items-center gap-2 font-medium text-foreground">
            <ShieldAlert className="size-4 text-amber-600" />
            <span>{t("settings.admin.runtimeEnvPolicyRiskTitle")}</span>
          </div>
          <p>{t("settings.admin.runtimeEnvPolicyRiskDescription")}</p>
          <p className="mt-2">
            {t("settings.admin.runtimeEnvPolicyScopeHint")}
          </p>
        </div>

        <div className="space-y-4">
          <div className="space-y-2">
            <div className="text-sm font-medium">
              {t("settings.admin.runtimeEnvPolicyMode")}
            </div>
            <Select
              value={mode}
              onValueChange={(value) => setMode(value as "disabled" | "opt_in")}
            >
              <SelectTrigger className="w-full md:w-64">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="opt_in">
                  {t("settings.admin.runtimeEnvPolicyModeOptIn")}
                </SelectItem>
                <SelectItem value="disabled">
                  {t("settings.admin.runtimeEnvPolicyModeDisabled")}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <AdminLabeledTextareaField
            label={t("settings.admin.runtimeEnvAllowlist")}
            value={allowlist}
            onChange={setAllowlist}
            placeholder="OPENAI_COMPATIBLE_*\nSERPAPI_API_KEY"
          />
          <AdminLabeledTextareaField
            label={t("settings.admin.runtimeEnvDenylist")}
            value={denylist}
            onChange={setDenylist}
            placeholder="PATH\nHOME\nPOCO_*"
          />

          <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
            {policy?.protected_prefixes?.length ||
            policy?.protected_keys?.length ? (
              <>
                <div>
                  {t("settings.admin.runtimeEnvProtectedPrefixes")}:{" "}
                  {(policy?.protected_prefixes ?? []).join(", ") || "-"}
                </div>
                <div className="mt-1">
                  {t("settings.admin.runtimeEnvProtectedKeys")}:{" "}
                  {(policy?.protected_keys ?? []).join(", ") || "-"}
                </div>
              </>
            ) : (
              t("settings.admin.runtimeEnvProtectedHint")
            )}
          </div>

          <div className="flex justify-end">
            <Button
              disabled={isSaving}
              onClick={() =>
                void onSave({
                  mode,
                  allowlist_patterns: parsePatterns(allowlist),
                  denylist_patterns: parsePatterns(denylist),
                })
              }
            >
              {t("settings.admin.update")}
            </Button>
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
