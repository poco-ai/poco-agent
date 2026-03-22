"use client";

import * as React from "react";
import { ExternalLink, Loader2, Save, Sparkles, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useEnvVarsStore } from "@/features/capabilities/env-vars/hooks/use-env-vars-store";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { emitSkillsMarketplaceConfigChanged } from "@/features/capabilities/skills/api/skills-marketplace-state";
import { useT } from "@/lib/i18n/client";

const SKILLSMP_API_KEY = "SKILLSMP_API_KEY";
const SKILLSMP_DOCS_URL = "https://skillsmp.com/docs/api";
const MASKED_KEY_PLACEHOLDER = "*******";

export function OtherSettingsTab() {
  const { t } = useT("translation");
  const { envVars, isLoading, savingEnvKey, upsertEnvVar, removeEnvVar } =
    useEnvVarsStore();

  const [keyInput, setKeyInput] = React.useState("");
  const [isEditingKey, setIsEditingKey] = React.useState(false);
  const [isStatusLoading, setIsStatusLoading] = React.useState(true);
  const [isMarketplaceConfigured, setIsMarketplaceConfigured] =
    React.useState(false);

  const customSkillsMpKey = React.useMemo(
    () =>
      envVars.find(
        (item) => item.scope === "user" && item.key === SKILLSMP_API_KEY,
      ) ?? null,
    [envVars],
  );

  React.useEffect(() => {
    let cancelled = false;

    const loadStatus = async () => {
      setIsStatusLoading(true);
      try {
        const response = await skillsService.getMarketplaceStatus();
        if (!cancelled) {
          setIsMarketplaceConfigured(response.configured);
        }
      } catch (error) {
        console.error("[Settings] Failed to load SkillsMP status:", error);
        if (!cancelled) {
          setIsMarketplaceConfigured(false);
        }
      } finally {
        if (!cancelled) {
          setIsStatusLoading(false);
        }
      }
    };

    void loadStatus();
    return () => {
      cancelled = true;
    };
  }, []);

  const isSaving = savingEnvKey === SKILLSMP_API_KEY;
  const hasCustomSkillsMpKey = Boolean(customSkillsMpKey);
  const isShowingMaskedKey =
    hasCustomSkillsMpKey && !isEditingKey && keyInput.length === 0;
  const displayKeyValue = isShowingMaskedKey
    ? MASKED_KEY_PLACEHOLDER
    : keyInput;
  const canSave = keyInput.trim().length > 0 && !isSaving;
  const canClear = Boolean(customSkillsMpKey) && !isSaving;

  const handleSave = React.useCallback(async () => {
    const trimmed = keyInput.trim();
    if (!trimmed) return;

    await upsertEnvVar({
      key: SKILLSMP_API_KEY,
      value: trimmed,
      description: t("settings.other.skillsmp.description"),
    });
    setKeyInput("");
    setIsEditingKey(false);

    try {
      const response = await skillsService.getMarketplaceStatus();
      setIsMarketplaceConfigured(response.configured);
      emitSkillsMarketplaceConfigChanged({ configured: response.configured });
    } catch (error) {
      console.error("[Settings] Failed to refresh SkillsMP status:", error);
    }
  }, [keyInput, t, upsertEnvVar]);

  const handleClear = React.useCallback(async () => {
    if (!customSkillsMpKey) return;

    await removeEnvVar(customSkillsMpKey.id);
    setKeyInput("");
    setIsEditingKey(false);
    try {
      const response = await skillsService.getMarketplaceStatus();
      setIsMarketplaceConfigured(response.configured);
      emitSkillsMarketplaceConfigChanged({ configured: response.configured });
    } catch (error) {
      console.error("[Settings] Failed to refresh SkillsMP status:", error);
      toast.error(t("settings.other.skillsmp.clearError"));
    }
  }, [customSkillsMpKey, removeEnvVar, t]);

  return (
    <div className="flex-1 space-y-8 overflow-y-auto p-6">
      <section className="space-y-4 rounded-3xl border border-border/60 bg-card/60 p-5 shadow-[var(--shadow-sm)]">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <div className="flex size-9 items-center justify-center rounded-2xl bg-muted text-foreground">
                <Sparkles className="size-4" />
              </div>
              <div>
                <h4 className="text-base font-medium text-foreground">
                  {t("settings.other.skillsmp.title")}
                </h4>
              </div>
            </div>
          </div>
          <div className="rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs text-muted-foreground">
            {isLoading || isStatusLoading
              ? t("settings.other.skillsmp.statusChecking")
              : isMarketplaceConfigured
                ? t("settings.other.skillsmp.statusReady")
                : t("settings.other.skillsmp.statusMissing")}
          </div>
        </div>

        <div className="space-y-2">
          <label htmlFor="skillsmp-api-key" className="sr-only">
            {t("settings.other.skillsmp.keyLabel")}
          </label>
          <Input
            id="skillsmp-api-key"
            type="password"
            value={displayKeyValue}
            onFocus={() => {
              if (isShowingMaskedKey) {
                setIsEditingKey(true);
              }
            }}
            onBlur={() => {
              if (keyInput.trim().length === 0) {
                setIsEditingKey(false);
              }
            }}
            onChange={(event) => {
              if (isShowingMaskedKey) {
                const normalizedValue = event.target.value.startsWith(
                  MASKED_KEY_PLACEHOLDER,
                )
                  ? event.target.value.slice(MASKED_KEY_PLACEHOLDER.length)
                  : event.target.value;
                setIsEditingKey(true);
                setKeyInput(normalizedValue);
                return;
              }
              setKeyInput(event.target.value);
            }}
            placeholder={
              hasCustomSkillsMpKey
                ? MASKED_KEY_PLACEHOLDER
                : t("settings.other.skillsmp.keyPlaceholder")
            }
            disabled={isSaving}
          />
          <p className="text-xs leading-6 text-muted-foreground">
            {t("settings.other.skillsmp.help")}{" "}
            <a
              href={SKILLSMP_DOCS_URL}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 text-foreground underline underline-offset-4"
            >
              {t("settings.other.skillsmp.docsLink")}
              <ExternalLink className="size-3" />
            </a>
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-2">
          {canClear ? (
            <Button
              type="button"
              variant="outline"
              size="icon"
              className="size-10"
              onClick={() => void handleClear()}
              disabled={isSaving}
              title={t("settings.other.skillsmp.clear")}
              aria-label={t("settings.other.skillsmp.clear")}
            >
              <Trash2 className="size-4" />
            </Button>
          ) : null}
          <Button
            type="button"
            size="icon"
            className="size-10"
            onClick={() => void handleSave()}
            disabled={!canSave}
            title={t("settings.other.skillsmp.save")}
            aria-label={t("settings.other.skillsmp.save")}
          >
            {isSaving ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <Save className="size-4" />
            )}
          </Button>
        </div>
      </section>
    </div>
  );
}
