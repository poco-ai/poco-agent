"use client";

import * as React from "react";
import { Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useT } from "@/lib/i18n/client";
import { ApiError } from "@/lib/errors";
import {
  getExecutionSettings,
  updateExecutionSettings,
} from "@/features/settings/api/execution-settings-api";
import type { ExecutionSettings } from "@/features/settings/types";

const EMPTY_SETTINGS: ExecutionSettings = {
  schema_version: "v1",
  hooks: { pipeline: [] },
  permissions: {},
  workspace: {},
  skills: {},
};

export function ExecutionSettingsTab() {
  const { t } = useT("translation");
  const [settings, setSettings] =
    React.useState<ExecutionSettings>(EMPTY_SETTINGS);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setIsLoading(true);
        const next = await getExecutionSettings();
        if (!cancelled) {
          setSettings(next);
        }
      } catch (error) {
        if (!cancelled) {
          console.error(
            "[ExecutionSettingsTab] Failed to load settings",
            error,
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const next = await updateExecutionSettings(settings);
      setSettings(next);
      toast.success(t("settings.execution.toasts.saved"));
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : t("settings.execution.toasts.saveFailed");
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" />
        {t("settings.execution.loading")}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h3 className="text-lg font-semibold">
          {t("settings.execution.title")}
        </h3>
        <p className="text-sm text-muted-foreground">
          {t("settings.execution.description")}
        </p>
      </div>

      <div className="space-y-3 rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-md">
        <Label>{t("settings.execution.workspaceStrategy")}</Label>
        <Select
          value={settings.workspace.checkout_strategy ?? "clone"}
          onValueChange={(value) =>
            setSettings((current) => ({
              ...current,
              workspace: {
                ...current.workspace,
                checkout_strategy:
                  value as ExecutionSettings["workspace"]["checkout_strategy"],
              },
            }))
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="clone">clone</SelectItem>
            <SelectItem value="worktree">worktree</SelectItem>
            <SelectItem value="sparse-clone">sparse-clone</SelectItem>
            <SelectItem value="sparse-worktree">sparse-worktree</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-3 rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-md">
        <div className="space-y-1">
          <h4 className="text-sm font-semibold">
            {t("settings.execution.hookPipeline")}
          </h4>
          <p className="text-xs text-muted-foreground">
            {t("settings.execution.hookPipelineHint")}
          </p>
        </div>

        <div className="space-y-3">
          {settings.hooks.pipeline.map((hook, index) => (
            <div
              key={`${hook.key}-${index}`}
              className="flex items-center justify-between gap-4 rounded-xl border border-border/60 bg-background/60 px-4 py-3"
            >
              <div className="space-y-1">
                <div className="font-mono text-sm">{hook.key}</div>
                <div className="text-xs text-muted-foreground">
                  {hook.phase} · order {hook.order}
                </div>
              </div>
              <Switch
                checked={hook.enabled}
                onCheckedChange={(checked) =>
                  setSettings((current) => ({
                    ...current,
                    hooks: {
                      pipeline: current.hooks.pipeline.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, enabled: checked }
                          : item,
                      ),
                    },
                  }))
                }
              />
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="mr-2 size-4 animate-spin" />
          ) : (
            <Save className="mr-2 size-4" />
          )}
          {t("settings.execution.save")}
        </Button>
      </div>
    </div>
  );
}
