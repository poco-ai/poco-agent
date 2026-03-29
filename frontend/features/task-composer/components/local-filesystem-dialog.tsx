"use client";

import * as React from "react";
import {
  FolderPlus,
  HardDrive,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import { localFilesystemApi } from "@/features/task-composer/api/local-filesystem-api";
import {
  createEmptyLocalMountDraftRow,
  toLocalMountDraftRows,
  validateLocalFilesystemDraft,
} from "@/features/task-composer/lib/local-filesystem";
import type {
  LocalFilesystemDraft,
  LocalFilesystemSupport,
  LocalMountDraftRow,
} from "@/features/task-composer/types/local-filesystem";

async function resolveDirectoryPath(name: string): Promise<string | null> {
  try {
    const res = await fetch(
      `/api/resolve-directory?name=${encodeURIComponent(name)}`,
    );
    if (!res.ok) return null;
    const data: { paths: string[] } = await res.json();
    // Only auto-fill when there's exactly one match to avoid ambiguity
    return data.paths.length === 1 ? data.paths[0] : null;
  } catch {
    return null;
  }
}

interface LocalFilesystemDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  value: LocalFilesystemDraft;
  onSave: (value: LocalFilesystemDraft) => Promise<void> | void;
  isSaving?: boolean;
  saveBehavior?: "draft" | "next_run";
}

const STATUS_AVAILABLE =
  "border-emerald-500/20 bg-emerald-500/8 text-emerald-700 dark:text-emerald-300";
const STATUS_UNAVAILABLE =
  "border-destructive/20 bg-destructive/8 text-destructive";

export function LocalFilesystemDialog({
  open,
  onOpenChange,
  value,
  onSave,
  isSaving = false,
  saveBehavior = "draft",
}: LocalFilesystemDialogProps) {
  const { t } = useT("translation");
  const [filesystemMode, setFilesystemMode] = React.useState<
    LocalFilesystemDraft["filesystem_mode"]
  >(value.filesystem_mode);
  const [rows, setRows] = React.useState<LocalMountDraftRow[]>(() =>
    toLocalMountDraftRows(value.local_mounts),
  );
  const [support, setSupport] = React.useState<LocalFilesystemSupport | null>(
    null,
  );
  const [isLoadingSupport, setIsLoadingSupport] = React.useState(false);
  const [supportLoadFailed, setSupportLoadFailed] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      return;
    }

    setFilesystemMode(value.filesystem_mode);
    setRows(toLocalMountDraftRows(value.local_mounts));
  }, [open, value.filesystem_mode, value.local_mounts]);

  React.useEffect(() => {
    if (!open) {
      return;
    }

    let cancelled = false;
    setIsLoadingSupport(true);
    setSupportLoadFailed(false);
    setSupport(null);

    void localFilesystemApi
      .getSupport()
      .then((nextSupport) => {
        if (cancelled) {
          return;
        }
        setSupport(nextSupport);
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        console.error(
          "[LocalFilesystemDialog] Failed to load local filesystem support:",
          error,
        );
        setSupportLoadFailed(true);
      })
      .finally(() => {
        if (!cancelled) {
          setIsLoadingSupport(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [open]);

  const handleRowChange = React.useCallback(
    (clientId: string, field: keyof LocalMountDraftRow, nextValue: string) => {
      setRows((prev) =>
        prev.map((row) =>
          row.client_id === clientId
            ? {
                ...row,
                [field]: nextValue,
              }
            : row,
        ),
      );
    },
    [],
  );

  const handleAddRow = React.useCallback(async () => {
    if (!("showDirectoryPicker" in window)) {
      toast.error(t("filesystem.picker.notSupported"));
      setRows((prev) => [...prev, createEmptyLocalMountDraftRow()]);
      return;
    }

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const handle = (await (window as any).showDirectoryPicker()) as {
        name: string;
      };
      const displayName = handle.name;
      const hostPath = await resolveDirectoryPath(displayName);

      setRows((prev) => [
        ...prev,
        createEmptyLocalMountDraftRow({
          host_path: hostPath ?? "",
          name: displayName,
        }),
      ]);

      if (!hostPath) {
        toast.warning(t("filesystem.picker.resolveFailed"));
      }
    } catch {
      // User cancelled the native picker — do nothing
    }
  }, [t]);

  const handleRemoveRow = React.useCallback((clientId: string) => {
    setRows((prev) => {
      const nextRows = prev.filter((row) => row.client_id !== clientId);
      return nextRows.length > 0 ? nextRows : [createEmptyLocalMountDraftRow()];
    });
  }, []);

  const handleSubmit = React.useCallback(async () => {
    const result = validateLocalFilesystemDraft(filesystemMode, rows, support);
    if (!result.ok || !result.value) {
      toast.error(
        t(
          result.error?.key || "hero.toasts.actionFailed",
          result.error?.values,
        ),
      );
      return;
    }

    try {
      await onSave(result.value);
      onOpenChange(false);
    } catch (error) {
      console.error(
        "[LocalFilesystemDialog] Failed to save local filesystem config:",
        error,
      );
      toast.error(t("filesystem.toasts.saveFailed"));
    }
  }, [filesystemMode, onOpenChange, onSave, rows, support, t]);

  const localModeLocked =
    support !== null &&
    !support.local_mount_available &&
    filesystemMode !== "local_mount";

  const statusIcon = support?.local_mount_available ? (
    <ShieldCheck className="size-4" />
  ) : (
    <ShieldAlert className="size-4" />
  );

  const statusClassName = support
    ? support.local_mount_available
      ? STATUS_AVAILABLE
      : STATUS_UNAVAILABLE
    : "border-border/60 bg-muted/40 text-foreground";

  const footerHintKey =
    saveBehavior === "next_run"
      ? "filesystem.messages.nextRun"
      : "filesystem.messages.draft";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-hidden sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{t("filesystem.title")}</DialogTitle>
          <DialogDescription>{t("filesystem.description")}</DialogDescription>
        </DialogHeader>

        <div className="flex max-h-[68vh] flex-col gap-5 overflow-y-auto pr-1">
          <div className="rounded-2xl border border-border/60 bg-muted/30 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <HardDrive className="size-4" />
                <span>{t("filesystem.status.title")}</span>
              </div>
              {isLoadingSupport ? (
                <Badge variant="secondary" className="gap-1 rounded-full">
                  <Loader2 className="size-3 animate-spin" />
                  {t("filesystem.status.loading")}
                </Badge>
              ) : (
                <div
                  className={cn(
                    "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium",
                    statusClassName,
                  )}
                >
                  {statusIcon}
                  <span>
                    {support
                      ? support.local_mount_available
                        ? t("filesystem.status.available")
                        : t("filesystem.status.unavailable")
                      : t("filesystem.status.unknown")}
                  </span>
                </div>
              )}
            </div>
            <div className="mt-3 flex flex-wrap items-start gap-3">
              <p className="max-w-2xl text-sm text-muted-foreground">
                {supportLoadFailed
                  ? t("filesystem.messages.supportUnknown")
                  : support?.deployment_mode === "cloud"
                    ? t("filesystem.messages.cloudDeployment")
                    : t("filesystem.messages.localDeployment")}
              </p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <button
              type="button"
              className={cn(
                "rounded-2xl border p-4 text-left transition-colors",
                filesystemMode === "sandbox"
                  ? "border-primary bg-primary/5"
                  : "border-border/60 bg-card hover:border-border",
              )}
              onClick={() => setFilesystemMode("sandbox")}
            >
              <div className="text-sm font-medium text-foreground">
                {t("filesystem.mode.sandboxTitle")}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {t("filesystem.mode.sandboxDescription")}
              </div>
            </button>
            <button
              type="button"
              disabled={localModeLocked}
              className={cn(
                "rounded-2xl border p-4 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60",
                filesystemMode === "local_mount"
                  ? "border-primary bg-primary/5"
                  : "border-border/60 bg-card hover:border-border",
              )}
              onClick={() => setFilesystemMode("local_mount")}
            >
              <div className="text-sm font-medium text-foreground">
                {t("filesystem.mode.localMountTitle")}
              </div>
              <div className="mt-1 text-sm text-muted-foreground">
                {t("filesystem.mode.localMountDescription")}
              </div>
            </button>
          </div>

          {filesystemMode === "local_mount" ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-sm font-medium text-foreground">
                    {t("filesystem.mounts.title")}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {t("filesystem.mounts.description")}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-xl"
                  onClick={handleAddRow}
                >
                  <FolderPlus className="size-4" />
                  {t("filesystem.actions.addMount")}
                </Button>
              </div>

              <div className="space-y-3">
                {rows.map((row, index) => (
                  <div
                    key={row.client_id}
                    className="rounded-2xl border border-border/60 bg-card p-4"
                  >
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <div className="text-sm font-medium text-foreground">
                        {t("filesystem.mounts.itemTitle", {
                          index: index + 1,
                        })}
                      </div>
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="size-8 rounded-xl text-muted-foreground"
                        onClick={() => handleRemoveRow(row.client_id)}
                        aria-label={t("filesystem.actions.removeMount")}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                    <div className="grid gap-3 md:grid-cols-[1fr_1.4fr_180px]">
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                          {t("filesystem.fields.name")}
                        </label>
                        <Input
                          value={row.name}
                          onChange={(event) =>
                            handleRowChange(
                              row.client_id,
                              "name",
                              event.target.value,
                            )
                          }
                          placeholder={t("filesystem.placeholders.name")}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                          {t("filesystem.fields.path")}
                        </label>
                        <Input
                          value={row.host_path}
                          onChange={(event) =>
                            handleRowChange(
                              row.client_id,
                              "host_path",
                              event.target.value,
                            )
                          }
                          placeholder={t("filesystem.placeholders.path")}
                        />
                      </div>
                      <div className="space-y-2">
                        <label className="text-sm font-medium text-foreground">
                          {t("filesystem.fields.access")}
                        </label>
                        <Select
                          value={row.access_mode}
                          onValueChange={(nextValue) =>
                            handleRowChange(
                              row.client_id,
                              "access_mode",
                              nextValue,
                            )
                          }
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="ro">
                              {t("filesystem.accessModes.ro")}
                            </SelectItem>
                            <SelectItem value="rw">
                              {t("filesystem.accessModes.rw")}
                            </SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
              {t("filesystem.messages.sandboxOnly")}
            </div>
          )}
        </div>

        <DialogFooter className="border-t border-border/60 pt-4 sm:items-center sm:justify-between">
          <p className="text-sm text-muted-foreground">{t(footerHintKey)}</p>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSaving}
            >
              {t("common.cancel")}
            </Button>
            <Button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={isSaving}
            >
              {isSaving ? <Loader2 className="size-4 animate-spin" /> : null}
              {saveBehavior === "next_run"
                ? t("filesystem.actions.save")
                : t("filesystem.actions.apply")}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
