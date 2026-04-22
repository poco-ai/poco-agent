import * as React from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ApiError } from "@/lib/errors";
import { useT } from "@/lib/i18n/client";

import type { McpDisplayItem } from "@/features/capabilities/mcp/hooks/use-mcp-catalog";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";

const DEFAULT_MCP_CONFIG = `{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "your-mcp-server"],
      "env": {}
    }
  }
}`;

const SENSITIVE_KEYWORDS = [
  "secret",
  "token",
  "password",
  "passwd",
  "auth",
  "bearer",
  "credential",
  "credentials",
  "api_key",
  "apikey",
  "api-token",
  "x-api-key",
  "access_key",
  "access_token",
  "refresh_token",
  "id_token",
  "private_key",
  "secret_key",
  "app_secret",
  "app_key",
  "client_key",
  "client_secret",
  "authorization",
  "sign",
  "signature",
  "signing_key",
  "webhook_secret",
  "session_key",
  "session_token",
  "license_key",
  "connection_string",
  "database_url",
  "dsn",
  "pat",
];

function normalizeKey(key: string): string {
  const trimmed = key.trim();
  if (!trimmed) return "";
  return trimmed
    .replace(/([a-z0-9])([A-Z])/g, "$1_$2")
    .replace(/[^a-zA-Z0-9]+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
}

function looksSensitiveKey(key: string): boolean {
  const normalized = normalizeKey(key);
  return SENSITIVE_KEYWORDS.some((keyword) => normalized.includes(keyword));
}

function maskString(value: string): string {
  const clean = value.trim();
  if (!clean) return value;
  if (clean.length <= 8) return "*".repeat(clean.length);
  return `${clean.slice(0, 4)}...${clean.slice(-4)}`;
}

function maskSensitiveStructure(value: unknown, parentKey?: string): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => maskSensitiveStructure(item, parentKey));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        maskSensitiveStructure(item, key),
      ]),
    );
  }

  if (typeof value === "string" && parentKey && looksSensitiveKey(parentKey)) {
    return maskString(value);
  }

  return value;
}

type ValidationItem = {
  path: string;
  message: string;
};

function extractValidationItems(error: unknown): ValidationItem[] {
  if (!(error instanceof ApiError)) return [];
  const details = error.details;
  if (
    !details ||
    typeof details !== "object" ||
    Array.isArray(details) ||
    !("data" in details)
  ) {
    return [];
  }
  const data = (details as { data?: unknown }).data;
  if (
    !data ||
    typeof data !== "object" ||
    Array.isArray(data) ||
    !("errors" in data)
  ) {
    return [];
  }
  const errors = (data as { errors?: unknown }).errors;
  if (!Array.isArray(errors)) return [];
  const result: ValidationItem[] = [];
  for (const item of errors) {
    if (!item || typeof item !== "object" || Array.isArray(item)) continue;
    const path = (item as { path?: unknown }).path;
    const message = (item as { message?: unknown }).message;
    if (typeof path !== "string" || typeof message !== "string") continue;
    result.push({ path, message });
  }
  return result;
}

interface McpSettingsDialogProps {
  item: McpDisplayItem | null;
  open: boolean;
  isNew?: boolean;
  readOnly?: boolean;
  onClose: () => void;
  onSave: (payload: {
    serverId?: number;
    name?: string;
    description?: string | null;
    serverConfig: Record<string, unknown>;
  }) => Promise<void>;
}

export function McpSettingsDialog({
  item,
  open,
  isNew = false,
  readOnly = false,
  onClose,
  onSave,
}: McpSettingsDialogProps) {
  const { t } = useT("translation");
  const [jsonConfig, setJsonConfig] = React.useState("{}");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [isSaving, setIsSaving] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [validationItems, setValidationItems] = React.useState<
    ValidationItem[]
  >([]);

  React.useEffect(() => {
    if (item) {
      const configObj =
        readOnly && item.server.scope === "system"
          ? maskSensitiveStructure(item.server.server_config || {})
          : item.server.server_config || {};
      setJsonConfig(JSON.stringify(configObj, null, 2));
      setName(item.server.name || "");
      setDescription(item.server.description || "");
    } else if (isNew) {
      setJsonConfig(DEFAULT_MCP_CONFIG);
      setName("");
      setDescription("");
    }
    setIsSaving(false);
    setSaveError(null);
    setValidationItems([]);
  }, [item, isNew, readOnly]);

  if (!item && !isNew) {
    return (
      <Dialog open={false} onOpenChange={onClose}>
        <DialogContent>
          <DialogTitle className="sr-only">
            {t("mcpSettings.configureServer")}
          </DialogTitle>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <CapabilityDialogContent
        title={t("mcpSettings.configureServer")}
        size="md"
        maxWidth="35rem"
        className="h-[56dvh] sm:h-[64dvh]"
        maxHeight="56dvh"
        desktopMaxHeight="64dvh"
        bodyClassName="flex h-full min-h-0 flex-col overflow-hidden bg-background px-6 py-6"
        footer={
          <DialogFooter className="grid grid-cols-2 gap-2">
            <Button variant="outline" onClick={onClose} className="w-full">
              {t("common.cancel")}
            </Button>
            <Button
              className="w-full"
              disabled={isSaving || readOnly}
              onClick={() => {
                if (isSaving) return;
                setSaveError(null);
                setValidationItems([]);
                setIsSaving(true);

                (async () => {
                  try {
                    const parsed = JSON.parse(jsonConfig);
                    const trimmedName = name.trim();
                    const trimmedDescription = description.trim();
                    if (isNew && !trimmedName) {
                      setSaveError(t("mcpSettings.nameRequired"));
                      return;
                    }
                    if (readOnly) {
                      onClose();
                      return;
                    }
                    await onSave({
                      serverId: item?.server.id,
                      name: trimmedName,
                      description: trimmedDescription || null,
                      serverConfig: parsed,
                    });
                    onClose();
                  } catch (error) {
                    if (error instanceof SyntaxError) {
                      setSaveError(t("mcpSettings.invalidJson"));
                      return;
                    }
                    const items = extractValidationItems(error);
                    setValidationItems(items);
                    if (error instanceof Error && error.message.trim()) {
                      setSaveError(error.message);
                    } else {
                      setSaveError(t("mcpSettings.saveFailed"));
                    }
                  } finally {
                    setIsSaving(false);
                  }
                })();
              }}
            >
              {t("common.save")}
            </Button>
          </DialogFooter>
        }
      >
        <div className="flex h-full min-h-0 flex-col gap-6">
          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t("mcpSettings.mcpName")}{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Input
              value={name}
              disabled={!isNew || readOnly}
              onChange={(e) => {
                setName(e.target.value);
                if (saveError || validationItems.length > 0) {
                  setSaveError(null);
                  setValidationItems([]);
                }
              }}
              className="bg-muted/50 font-mono text-sm"
            />
          </div>

          <div className="space-y-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t("mcpSettings.descriptionRecommended")}
            </Label>
            <Input
              value={description}
              disabled={readOnly}
              onChange={(e) => {
                setDescription(e.target.value);
                if (saveError || validationItems.length > 0) {
                  setSaveError(null);
                  setValidationItems([]);
                }
              }}
              placeholder={t("mcpSettings.descriptionPlaceholder")}
              className="bg-muted/50 text-sm"
            />
            <p className="text-xs text-muted-foreground">
              {t("mcpSettings.descriptionHint")}
            </p>
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-2">
            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              {t("mcpSettings.fullJsonConfig")}
            </Label>
            <p className="text-xs text-muted-foreground">
              {readOnly && item?.server.scope === "system"
                ? t(
                    "mcpSettings.maskedJsonConfigHint",
                    "System MCP configs are masked in read-only view.",
                  )
                : t(
                    "mcpSettings.fullJsonConfigHint",
                    'Paste a Claude-style MCP config, e.g. {"mcpServers": {...}}',
                  )}
            </p>
            <Textarea
              value={jsonConfig}
              disabled={readOnly}
              onChange={(e) => {
                setJsonConfig(e.target.value);
                if (saveError || validationItems.length > 0) {
                  setSaveError(null);
                  setValidationItems([]);
                }
              }}
              className="h-full min-h-0 flex-1 resize-none bg-muted/50 p-4 font-mono text-sm"
              spellCheck={false}
            />
          </div>

          {saveError || validationItems.length > 0 ? (
            <Alert
              variant="destructive"
              className="border-destructive/50 bg-destructive/10 text-destructive"
            >
              <AlertTriangle className="size-4" />
              <AlertTitle>{t("mcpSettings.saveFailed")}</AlertTitle>
              <AlertDescription>
                {saveError ? <p>{saveError}</p> : null}
                {validationItems.length > 0 ? (
                  <ul className="mt-2 list-disc pl-5 space-y-1">
                    {validationItems.map((item, index) => (
                      <li
                        key={`${item.path}-${index}`}
                        className="font-mono text-xs"
                      >
                        {item.path}: {item.message}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </AlertDescription>
            </Alert>
          ) : null}
        </div>
      </CapabilityDialogContent>
    </Dialog>
  );
}
