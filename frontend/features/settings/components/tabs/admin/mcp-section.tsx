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
  McpServerCreateInput,
  McpServerUpdateInput,
} from "@/features/capabilities/mcp/types";
import type { AdminMcpServer } from "@/features/settings/api/admin-api";
import { useT } from "@/lib/i18n/client";

import {
  AdminCreateActions,
  AdminEditActions,
  AdminItemActions,
  AdminLabeledInputField,
  AdminLabeledTextareaField,
  AdminPolicyHint,
  AdminPolicySwitchField,
  AdminSectionError,
  AdminSectionLoading,
  ListItem,
  parseJsonObject,
  summarizeJson,
} from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

const DEFAULT_MCP_CONFIG = `{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "your-mcp-server"],
      "env": {}
    }
  }
}`;

interface McpEditState {
  name: string;
  description: string;
  serverConfig: string;
  defaultEnabled: boolean;
  forceEnabled: boolean;
}

interface AdminMcpSectionProps {
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  mcpServers: AdminMcpServer[];
  onRetry: () => void;
  onCreate: (input: McpServerCreateInput) => Promise<void>;
  onUpdate: (serverId: number, input: McpServerUpdateInput) => Promise<void>;
  onDelete: (serverId: number) => Promise<void>;
}

export function AdminMcpSection({
  isLoading,
  hasError,
  isSaving,
  mcpServers,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminMcpSectionProps) {
  const { t } = useT("translation");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [editingServer, setEditingServer] =
    React.useState<AdminMcpServer | null>(null);
  const [editState, setEditState] = React.useState<McpEditState>({
    name: "",
    description: "",
    serverConfig: "{}",
    defaultEnabled: false,
    forceEnabled: false,
  });

  const filteredMcpServers = React.useMemo(() => {
    if (!searchQuery) return mcpServers;
    const lowerQuery = searchQuery.toLowerCase();
    return mcpServers.filter((server) => {
      return (
        server.name.toLowerCase().includes(lowerQuery) ||
        (server.description || "").toLowerCase().includes(lowerQuery) ||
        JSON.stringify(server.masked_server_config || {})
          .toLowerCase()
          .includes(lowerQuery)
      );
    });
  }, [mcpServers, searchQuery]);

  const openCreateDialog = React.useCallback(() => {
    setEditingServer(null);
    setEditState({
      name: "",
      description: "",
      serverConfig: DEFAULT_MCP_CONFIG,
      defaultEnabled: false,
      forceEnabled: false,
    });
    setDialogOpen(true);
  }, []);

  const openEditDialog = React.useCallback((item: AdminMcpServer) => {
    setEditingServer(item);
    setEditState({
      name: item.name,
      description: item.description ?? "",
      serverConfig: JSON.stringify(item.server_config ?? {}, null, 2),
      defaultEnabled: item.default_enabled,
      forceEnabled: item.force_enabled,
    });
    setDialogOpen(true);
  }, []);

  const closeDialog = React.useCallback(() => {
    setDialogOpen(false);
    setEditingServer(null);
  }, []);

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.mcpTitle")}
        description={t("settings.admin.mcpDescription")}
        summary={`${t("settings.admin.mcpTitle")} · ${filteredMcpServers.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.mcpLibrary.searchPlaceholder")}
        createLabel={t("library.mcpLibrary.addCard", "Add MCP")}
        onCreate={openCreateDialog}
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
            {filteredMcpServers.map((item) => (
              <ListItem
                key={item.id}
                title={item.name}
                description={
                  item.description || summarizeJson(item.masked_server_config)
                }
                badge={
                  item.has_sensitive_data ? (
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
              {editingServer
                ? editingServer.name
                : t("settings.admin.mcpTitle")}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <AdminLabeledInputField
                label={t("settings.admin.mcpNamePlaceholder")}
                value={editState.name}
                onChange={(value) =>
                  setEditState((current) => ({ ...current, name: value }))
                }
              />
              <AdminLabeledInputField
                label={t("settings.admin.envDescriptionPlaceholder")}
                value={editState.description}
                onChange={(value) =>
                  setEditState((current) => ({
                    ...current,
                    description: value,
                  }))
                }
              />
              <AdminPolicySwitchField
                label={t("settings.admin.policyDefaultEnabled")}
                checked={editState.defaultEnabled}
                onCheckedChange={(checked) =>
                  setEditState((current) => ({
                    ...current,
                    defaultEnabled: checked,
                  }))
                }
              />
              <AdminPolicySwitchField
                label={t("settings.admin.policyForceEnabled")}
                checked={editState.forceEnabled}
                onCheckedChange={(checked) =>
                  setEditState((current) => ({
                    ...current,
                    forceEnabled: checked,
                  }))
                }
              />
            </div>
            <AdminLabeledTextareaField
              label={t("settings.admin.jsonConfig")}
              value={editState.serverConfig}
              onChange={(value) =>
                setEditState((current) => ({ ...current, serverConfig: value }))
              }
              className="min-h-32"
              placeholder={DEFAULT_MCP_CONFIG}
            />
            <div className="text-xs text-muted-foreground">
              {t(
                "settings.admin.mcpSecretHint",
                "Sensitive values are masked in the list, but editing shows the full JSON config.",
              )}
            </div>
          </div>
          <DialogFooter>
            {editingServer ? (
              <AdminEditActions
                isSaving={isSaving}
                onCancel={closeDialog}
                onSave={async () => {
                  const serverConfigText = editState.serverConfig.trim();
                  const payload = {
                    name: editState.name.trim(),
                    description: editState.description || undefined,
                    server_config: parseJsonObject(
                      serverConfigText || "{}",
                      t("settings.admin.invalidJsonObject"),
                    ),
                    default_enabled: editState.defaultEnabled,
                    force_enabled: editState.forceEnabled,
                  };
                  await onUpdate(editingServer.id, {
                    ...payload,
                  });
                  closeDialog();
                }}
              />
            ) : (
              <AdminCreateActions
                isSaving={isSaving}
                onCreate={async () => {
                  const serverConfigText = editState.serverConfig.trim();
                  const payload = {
                    name: editState.name.trim(),
                    description: editState.description || undefined,
                    server_config: parseJsonObject(
                      serverConfigText || "{}",
                      t("settings.admin.invalidJsonObject"),
                    ),
                    default_enabled: editState.defaultEnabled,
                    force_enabled: editState.forceEnabled,
                  };
                  if (!payload.name) {
                    throw new Error(t("settings.admin.mcpNameRequired"));
                  }
                  await onCreate(payload);
                  closeDialog();
                }}
              />
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
