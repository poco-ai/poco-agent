import * as React from "react";
import { KeySquare, RefreshCw, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type {
  AdminEnvVar,
  AdminSystemEnvVarCreateInput,
  AdminSystemEnvVarUpdateInput,
  RuntimeEnvPolicy,
  RuntimeVisibility,
} from "@/features/settings/api/admin-api";
import { useT } from "@/lib/i18n/client";

import {
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  SectionCard,
} from "./shared";

const SKILLSMP_API_KEY = "SKILLSMP_API_KEY";

interface EnvVarEditState {
  value: string;
  description: string;
  runtimeVisibility: RuntimeVisibility;
}

interface AdminEnvVarsSectionProps {
  envVars: AdminEnvVar[];
  runtimeEnvPolicy: RuntimeEnvPolicy | null;
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRefresh: () => void;
  onRetry: () => void;
  onCreate: (input: AdminSystemEnvVarCreateInput) => Promise<void>;
  onUpdate: (
    envVarId: number,
    input: AdminSystemEnvVarUpdateInput,
  ) => Promise<void>;
  onDelete: (envVarId: number) => Promise<void>;
}

export function AdminEnvVarsSection({
  envVars,
  runtimeEnvPolicy,
  isLoading,
  hasError,
  isSaving,
  onRefresh,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminEnvVarsSectionProps) {
  const { t } = useT("translation");
  const [newEnvKey, setNewEnvKey] = React.useState("");
  const [newEnvValue, setNewEnvValue] = React.useState("");
  const [newEnvDescription, setNewEnvDescription] = React.useState("");
  const [newRuntimeVisibility, setNewRuntimeVisibility] =
    React.useState<RuntimeVisibility>("none");
  const [editingEnvVarId, setEditingEnvVarId] = React.useState<number | null>(
    null,
  );
  const [envEditState, setEnvEditState] =
    React.useState<EnvVarEditState | null>(null);

  const resetEditingState = React.useCallback(() => {
    setEditingEnvVarId(null);
    setEnvEditState(null);
  }, []);

  const isProtectedRuntimeKey = React.useCallback(
    (key: string) => {
      const normalizedKey = key.trim();
      if (!normalizedKey || !runtimeEnvPolicy) {
        return false;
      }
      if ((runtimeEnvPolicy.protected_keys ?? []).includes(normalizedKey)) {
        return true;
      }
      return (runtimeEnvPolicy.protected_prefixes ?? []).some((prefix) =>
        normalizedKey.startsWith(prefix),
      );
    },
    [runtimeEnvPolicy],
  );

  const newKeyIsProtected = isProtectedRuntimeKey(newEnvKey);

  const handleCreate = React.useCallback(async () => {
    if (!newEnvKey.trim()) {
      throw new Error(t("settings.admin.envKeyRequired"));
    }
    await onCreate({
      key: newEnvKey.trim(),
      value: newEnvValue,
      description: newEnvDescription || undefined,
      runtime_visibility: newRuntimeVisibility,
    });
    setNewEnvKey("");
    setNewEnvValue("");
    setNewEnvDescription("");
    setNewRuntimeVisibility("none");
  }, [
    newEnvDescription,
    newEnvKey,
    newEnvValue,
    newRuntimeVisibility,
    onCreate,
    t,
  ]);

  const handleDelete = React.useCallback(
    async (envVarId: number) => {
      try {
        await onDelete(envVarId);
      } catch {
        // Error toast is handled upstream.
      }
    },
    [onDelete],
  );

  const handleUpdate = React.useCallback(
    async (envVarId: number) => {
      if (!envEditState) {
        return;
      }
      await onUpdate(envVarId, {
        value: envEditState.value || undefined,
        description: envEditState.description || undefined,
        runtime_visibility: envEditState.runtimeVisibility,
      });
      resetEditingState();
    },
    [envEditState, onUpdate, resetEditingState],
  );

  return (
    <SectionCard
      title={t("settings.admin.envTitle")}
      description={t("settings.admin.envDescription")}
      actions={
        <Button variant="outline" size="sm" onClick={onRefresh}>
          <RefreshCw className="mr-2 size-4" />
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
        <div className="rounded-xl border border-border bg-muted/20 p-4">
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-muted text-muted-foreground">
              <KeySquare className="size-4" />
            </div>
            <div className="min-w-0 space-y-1">
              <div className="font-medium">{SKILLSMP_API_KEY}</div>
              <div className="text-sm text-muted-foreground">
                {t("settings.admin.skillsMpHelp")}
              </div>
            </div>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <Input
            value={newEnvKey}
            onChange={(e) => setNewEnvKey(e.target.value)}
            placeholder={t("settings.admin.envKeyPlaceholder")}
          />
          <Input
            value={newEnvValue}
            onChange={(e) => setNewEnvValue(e.target.value)}
            placeholder={t("settings.admin.envValuePlaceholder")}
          />
          <Input
            value={newEnvDescription}
            onChange={(e) => setNewEnvDescription(e.target.value)}
            placeholder={t("settings.admin.envDescriptionPlaceholder")}
          />
        </div>
        <div className="max-w-sm">
          <Label className="mb-2 block">
            {t("settings.admin.runtimeVisibilityLabel")}
          </Label>
          <Select
            value={newRuntimeVisibility}
            onValueChange={(value) =>
              setNewRuntimeVisibility(value as RuntimeVisibility)
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">
                {t("settings.admin.runtimeVisibilityNone")}
              </SelectItem>
              <SelectItem value="admins_only">
                {t("settings.admin.runtimeVisibilityAdminsOnly")}
              </SelectItem>
              <SelectItem value="all_users">
                {t("settings.admin.runtimeVisibilityAllUsers")}
              </SelectItem>
            </SelectContent>
          </Select>
          {newKeyIsProtected ? (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-300">
              {t("settings.admin.runtimeVisibilityProtectedWarning")}
            </p>
          ) : null}
        </div>
        <div className="flex justify-end">
          <Button
            onClick={() => {
              void handleCreate().catch(() => {
                // Error toast is handled upstream.
              });
            }}
            disabled={isSaving}
          >
            {t("settings.admin.create")}
          </Button>
        </div>
        <div className="space-y-2">
          {envVars.map((item) => (
            <ListItem
              key={item.id}
              title={item.key}
              description={item.description || item.masked_value || "-"}
              badge={
                <div className="flex gap-2">
                  <Badge variant={item.is_set ? "secondary" : "outline"}>
                    {item.is_set
                      ? t("settings.admin.valueConfigured")
                      : t("settings.admin.valueEmpty")}
                  </Badge>
                  <Badge variant="outline">
                    {item.runtime_visibility === "none"
                      ? t("settings.admin.runtimeVisibilityNone")
                      : item.runtime_visibility === "admins_only"
                        ? t("settings.admin.runtimeVisibilityAdminsOnly")
                        : t("settings.admin.runtimeVisibilityAllUsers")}
                  </Badge>
                </div>
              }
              danger={
                <>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditingEnvVarId(item.id);
                      setEnvEditState({
                        value: "",
                        description: item.description ?? "",
                        runtimeVisibility: item.runtime_visibility,
                      });
                    }}
                    disabled={isSaving}
                  >
                    {t("settings.admin.edit")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => {
                      void handleDelete(item.id);
                    }}
                    disabled={isSaving}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </>
              }
            >
              {editingEnvVarId === item.id && envEditState ? (
                <div className="space-y-3">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label>{t("settings.admin.envValuePlaceholder")}</Label>
                      <Input
                        value={envEditState.value}
                        onChange={(e) =>
                          setEnvEditState((current) =>
                            current
                              ? { ...current, value: e.target.value }
                              : current,
                          )
                        }
                        placeholder={t("settings.admin.envUpdateHint")}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>
                        {t("settings.admin.envDescriptionPlaceholder")}
                      </Label>
                      <Input
                        value={envEditState.description}
                        onChange={(e) =>
                          setEnvEditState((current) =>
                            current
                              ? { ...current, description: e.target.value }
                              : current,
                          )
                        }
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label>{t("settings.admin.runtimeVisibilityLabel")}</Label>
                    <Select
                      value={envEditState.runtimeVisibility}
                      onValueChange={(value) =>
                        setEnvEditState((current) =>
                          current
                            ? {
                                ...current,
                                runtimeVisibility: value as RuntimeVisibility,
                              }
                            : current,
                        )
                      }
                    >
                      <SelectTrigger className="max-w-sm">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="none">
                          {t("settings.admin.runtimeVisibilityNone")}
                        </SelectItem>
                        <SelectItem value="admins_only">
                          {t("settings.admin.runtimeVisibilityAdminsOnly")}
                        </SelectItem>
                        <SelectItem value="all_users">
                          {t("settings.admin.runtimeVisibilityAllUsers")}
                        </SelectItem>
                      </SelectContent>
                    </Select>
                    {isProtectedRuntimeKey(item.key) ? (
                      <p className="text-xs text-amber-700 dark:text-amber-300">
                        {t("settings.admin.runtimeVisibilityProtectedWarning")}
                      </p>
                    ) : null}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {t("settings.admin.maskedUpdateHint")}
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button
                      variant="outline"
                      onClick={resetEditingState}
                      disabled={isSaving}
                    >
                      {t("settings.admin.cancel")}
                    </Button>
                    <Button
                      onClick={() => {
                        void handleUpdate(item.id).catch(() => {
                          // Error toast is handled upstream.
                        });
                      }}
                      disabled={isSaving}
                    >
                      {t("settings.admin.update")}
                    </Button>
                  </div>
                </div>
              ) : null}
            </ListItem>
          ))}
        </div>
      </div>
    </SectionCard>
  );
}
