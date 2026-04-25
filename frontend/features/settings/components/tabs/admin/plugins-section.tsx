"use client";

import * as React from "react";

import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type {
  PluginCreateInput,
  PluginUpdateInput,
} from "@/features/capabilities/plugins/types";
import { PluginImportDialog } from "@/features/capabilities/plugins/components/plugin-import-dialog";
import type { AdminPlugin } from "@/features/settings/api/admin-api";
import { adminApi } from "@/features/settings/api/admin-api";
import { useT } from "@/lib/i18n/client";

import {
  AdminEditActions,
  AdminItemActions,
  AdminLabeledInputField,
  AdminLabeledTextareaField,
  AdminMaskedUpdateHint,
  AdminPolicyHint,
  AdminPolicySwitchField,
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  parseJsonObject,
  summarizeJson,
} from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface PluginEditState {
  name: string;
  description: string;
  version: string;
  entry: string;
  manifest: string;
  defaultEnabled: boolean;
  forceEnabled: boolean;
}

interface AdminPluginsSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  plugins: AdminPlugin[];
  onRetry: () => void;
  onCreate: (input: PluginCreateInput) => Promise<void>;
  onUpdate: (pluginId: number, input: PluginUpdateInput) => Promise<void>;
  onDelete: (pluginId: number) => Promise<void>;
}

export function AdminPluginsSection({
  isLoading,
  hasError,
  isSaving,
  plugins,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminPluginsSectionProps) {
  const { t } = useT("translation");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [importOpen, setImportOpen] = React.useState(false);
  const [editingPlugin, setEditingPlugin] = React.useState<AdminPlugin | null>(
    null,
  );
  const [pluginEditState, setPluginEditState] = React.useState<PluginEditState>(
    {
      name: "",
      description: "",
      version: "",
      entry: "{}",
      manifest: "{}",
      defaultEnabled: false,
      forceEnabled: false,
    },
  );

  const filteredPlugins = React.useMemo(() => {
    if (!searchQuery) return plugins;
    const lowerQuery = searchQuery.toLowerCase();
    return plugins.filter((item) => {
      return (
        item.name.toLowerCase().includes(lowerQuery) ||
        (item.description || "").toLowerCase().includes(lowerQuery) ||
        JSON.stringify(item.masked_entry || {})
          .toLowerCase()
          .includes(lowerQuery) ||
        JSON.stringify(item.masked_manifest || {})
          .toLowerCase()
          .includes(lowerQuery)
      );
    });
  }, [plugins, searchQuery]);

  const openEditDialog = React.useCallback((item: AdminPlugin) => {
    setEditingPlugin(item);
    setPluginEditState({
      name: item.name,
      description: item.description ?? "",
      version: item.version ?? "",
      entry: "",
      manifest: "",
      defaultEnabled: item.default_enabled,
      forceEnabled: item.force_enabled,
    });
    setDialogOpen(true);
  }, []);

  const closeDialog = React.useCallback(() => {
    setDialogOpen(false);
    setEditingPlugin(null);
  }, []);

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.pluginsTitle")}
        description={t("settings.admin.pluginsDescription")}
        summary={`${t("settings.admin.pluginsTitle")} · ${filteredPlugins.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.pluginsPage.searchPlaceholder")}
        createLabel={t("library.pluginsPage.addCard")}
        onCreate={() => setImportOpen(true)}
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <AdminPolicyHint />
          <div className="space-y-2">
            {filteredPlugins.map((item) => (
              <ListItem
                key={item.id}
                title={item.name}
                description={
                  item.description || summarizeJson(item.masked_entry)
                }
                badge={
                  item.entry_has_sensitive_data ||
                  item.manifest_has_sensitive_data ? (
                    <Badge variant="outline">
                      {t("settings.admin.masked")}
                    </Badge>
                  ) : undefined
                }
                danger={
                  <AdminItemActions
                    isSaving={isSaving}
                    onEdit={() => openEditDialog(item)}
                    onDelete={() => onDelete(item.id)}
                  />
                }
              />
            ))}
          </div>
        </div>
      </AdminCatalogShell>

      <Dialog open={dialogOpen} onOpenChange={(open) => !open && closeDialog()}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {editingPlugin
                ? editingPlugin.name
                : t("settings.admin.pluginsTitle")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-3">
              <AdminLabeledInputField
                label={t("settings.admin.pluginNamePlaceholder")}
                value={pluginEditState.name}
                onChange={(value) =>
                  setPluginEditState((current) => ({
                    ...current,
                    name: value,
                  }))
                }
              />
              <AdminLabeledInputField
                label={t("settings.admin.envDescriptionPlaceholder")}
                value={pluginEditState.description}
                onChange={(value) =>
                  setPluginEditState((current) => ({
                    ...current,
                    description: value,
                  }))
                }
              />
              <AdminLabeledInputField
                label={t("settings.admin.pluginVersionPlaceholder")}
                value={pluginEditState.version}
                onChange={(value) =>
                  setPluginEditState((current) => ({
                    ...current,
                    version: value,
                  }))
                }
              />
              <AdminPolicySwitchField
                label={t("settings.admin.policyDefaultEnabled")}
                checked={pluginEditState.defaultEnabled}
                onCheckedChange={(checked) =>
                  setPluginEditState((current) => ({
                    ...current,
                    defaultEnabled: checked,
                  }))
                }
              />
              <AdminPolicySwitchField
                label={t("settings.admin.policyForceEnabled")}
                checked={pluginEditState.forceEnabled}
                onCheckedChange={(checked) =>
                  setPluginEditState((current) => ({
                    ...current,
                    forceEnabled: checked,
                  }))
                }
              />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <AdminLabeledTextareaField
                label={t("settings.admin.pluginEntry")}
                value={pluginEditState.entry}
                onChange={(value) =>
                  setPluginEditState((current) => ({
                    ...current,
                    entry: value,
                  }))
                }
                className="min-h-32"
                placeholder={t("settings.admin.reenterConfigPlaceholder")}
              />
              <AdminLabeledTextareaField
                label={t("settings.admin.pluginManifest")}
                value={pluginEditState.manifest}
                onChange={(value) =>
                  setPluginEditState((current) => ({
                    ...current,
                    manifest: value,
                  }))
                }
                className="min-h-32"
                placeholder={t("settings.admin.reenterConfigPlaceholder")}
              />
            </div>
            <AdminMaskedUpdateHint />
          </div>
          <DialogFooter>
            <AdminEditActions
              isSaving={isSaving}
              onCancel={closeDialog}
              onSave={async () => {
                const entryText = pluginEditState.entry.trim();
                const manifestText = pluginEditState.manifest.trim();
                const payload: PluginCreateInput = {
                  name: pluginEditState.name.trim(),
                  description: pluginEditState.description || undefined,
                  version: pluginEditState.version || undefined,
                  entry: parseJsonObject(
                    entryText || "{}",
                    t("settings.admin.invalidJsonObject"),
                  ),
                  manifest: parseJsonObject(
                    manifestText || "{}",
                    t("settings.admin.invalidJsonObject"),
                  ),
                  default_enabled: pluginEditState.defaultEnabled,
                  force_enabled: pluginEditState.forceEnabled,
                };

                if (!editingPlugin) {
                  if (!payload.name) {
                    throw new Error(t("settings.admin.pluginNameRequired"));
                  }
                  await onCreate(payload);
                } else {
                  await onUpdate(editingPlugin.id, {
                    ...payload,
                    entry: entryText ? payload.entry : undefined,
                    manifest: manifestText ? payload.manifest : undefined,
                  });
                }
                closeDialog();
              }}
            />
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <PluginImportDialog
        open={importOpen}
        onClose={() => setImportOpen(false)}
        onImported={async () => {
          setImportOpen(false);
          await onRetry();
        }}
        importApi={{
          discover: adminApi.importSystemPluginDiscover,
          commit: adminApi.importSystemPluginCommit,
          getJob: adminApi.getSystemPluginImportJob,
        }}
      />
    </>
  );
}
