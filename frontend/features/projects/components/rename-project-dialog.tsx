"use client";

import * as React from "react";
import { ChevronDown } from "lucide-react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n/client";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { ModelSelector } from "@/features/chat/components/chat/model-selector";
import { useModelCatalog } from "@/features/chat/hooks/use-model-catalog";
import type { ModelSelection } from "@/features/chat/lib/model-catalog";
import type { LocalMountConfig } from "@/features/chat/types/api/session";
import {
  createEmptyLocalMountDraftRow,
  validateLocalFilesystemDraft,
} from "@/features/task-composer/lib/local-filesystem";
import type { LocalMountDraftRow } from "@/features/task-composer/types/local-filesystem";
import {
  pickLocalDirectory,
  supportsNativeDirectoryPicker,
} from "@/lib/local-directory-picker";
import { createRenameProjectDialogState } from "@/features/projects/lib/rename-project-dialog-state";
import { LocalMountEditor } from "@/components/shared/local-mount-editor";
import { LocalFilesystemModeSelector } from "@/components/shared/local-filesystem-mode-selector";

function serializeLocalMounts(mounts: LocalMountConfig[]): string {
  return JSON.stringify(
    mounts.map((mount) => ({
      id: mount.id,
      name: mount.name,
      host_path: mount.host_path,
      access_mode: mount.access_mode ?? "ro",
    })),
  );
}

interface RenameProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectName: string;
  projectDescription?: string | null;
  projectDefaultModel?: string | null;
  projectLocalMounts?: LocalMountConfig[] | null;
  onRename: (
    newName: string,
    newDescription?: string | null,
    defaultModel?: string | null,
    localMounts?: LocalMountConfig[],
  ) => void;
  allowDescriptionEdit?: boolean;
}

export function RenameProjectDialog({
  open,
  onOpenChange,
  projectName,
  projectDescription,
  projectDefaultModel,
  projectLocalMounts,
  onRename,
  allowDescriptionEdit = false,
}: RenameProjectDialogProps) {
  const { t } = useT("translation");
  const { modelOptions, isLoading: isLoadingModelCatalog } = useModelCatalog({
    enabled: open,
  });
  const initialState = React.useMemo(
    () =>
      createRenameProjectDialogState({
        projectName,
        projectDescription,
        projectDefaultModel,
        projectLocalMounts,
      }),
    [projectDefaultModel, projectDescription, projectLocalMounts, projectName],
  );
  const [name, setName] = React.useState(initialState.name);
  const [description, setDescription] = React.useState(
    initialState.description,
  );
  const [advancedOpen, setAdvancedOpen] = React.useState(false);
  const [modelSelection, setModelSelection] =
    React.useState<ModelSelection | null>(initialState.modelSelection);
  const [filesystemMode, setFilesystemMode] = React.useState(
    initialState.filesystemMode,
  );
  const [mountRows, setMountRows] = React.useState<LocalMountDraftRow[]>(
    initialState.mountRows,
  );
  const inputRef = React.useRef<HTMLInputElement>(null);

  const defaultSelection = React.useMemo(() => {
    const defaultOption = modelOptions.find((option) => option.isDefault);
    return defaultOption
      ? {
          modelId: defaultOption.modelId,
          providerId: defaultOption.providerId,
        }
      : null;
  }, [modelOptions]);

  React.useEffect(() => {
    if (!open) {
      return;
    }

    setName(initialState.name);
    setDescription(initialState.description);
    setModelSelection(initialState.modelSelection);
    setFilesystemMode(initialState.filesystemMode);
    setMountRows(initialState.mountRows);
    setAdvancedOpen(false);
  }, [initialState, open]);

  React.useEffect(() => {
    if (open) {
      setTimeout(() => {
        inputRef.current?.focus();
        inputRef.current?.select();
      }, 50);
    }
  }, [open]);

  const handleRowChange = React.useCallback(
    (clientId: string, field: keyof LocalMountDraftRow, nextValue: string) => {
      setMountRows((prev) =>
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
    if (!supportsNativeDirectoryPicker()) {
      toast.error(t("filesystem.picker.notSupported"));
      setMountRows((prev) => [...prev, createEmptyLocalMountDraftRow()]);
      return;
    }

    setFilesystemMode("local_mount");
    try {
      const pickedDirectory = await pickLocalDirectory();
      if (!pickedDirectory) {
        return;
      }

      setMountRows((prev) => [
        ...prev,
        createEmptyLocalMountDraftRow({
          host_path: pickedDirectory.hostPath ?? "",
          name: pickedDirectory.displayName,
        }),
      ]);

      if (!pickedDirectory.hostPath) {
        toast.warning(t("filesystem.picker.resolveFailed"));
      }
    } catch {
      // User cancelled the native picker — do nothing
    }
  }, [t]);

  const handleRemoveRow = React.useCallback((clientId: string) => {
    setMountRows((prev) => {
      const nextRows = prev.filter((row) => row.client_id !== clientId);
      return nextRows.length > 0 ? nextRows : [createEmptyLocalMountDraftRow()];
    });
  }, []);

  const handleFilesystemModeChange = React.useCallback(
    (nextMode: "sandbox" | "local_mount") => {
      setFilesystemMode(nextMode);
      if (nextMode === "local_mount" && mountRows.length === 0) {
        setMountRows([createEmptyLocalMountDraftRow()]);
      }
    },
    [mountRows.length],
  );

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();

    const validationResult = validateLocalFilesystemDraft(
      filesystemMode,
      mountRows,
      null,
    );
    if (!validationResult.ok || !validationResult.value) {
      toast.error(
        t(
          validationResult.error?.key || "hero.toasts.actionFailed",
          validationResult.error?.values,
        ),
      );
      return;
    }

    const trimmed = name.trim();
    const trimmedDescription = description.trim();
    const currentDescription = projectDescription?.trim() ?? "";
    const currentDefaultModel = projectDefaultModel?.trim() ?? "";
    const nextDescription = trimmedDescription || null;
    const nextDefaultModel = modelSelection?.modelId?.trim() || null;
    const nextLocalMounts = validationResult.value.local_mounts;
    const hasNameChange = trimmed !== projectName;
    const hasDescriptionChange =
      allowDescriptionEdit && trimmedDescription !== currentDescription;
    const hasDefaultModelChange =
      nextDefaultModel !== (currentDefaultModel || null);
    const hasLocalMountChange =
      serializeLocalMounts(nextLocalMounts) !==
      serializeLocalMounts(projectLocalMounts ?? []);

    if (
      !trimmed ||
      (!hasNameChange &&
        !hasDescriptionChange &&
        !hasDefaultModelChange &&
        !hasLocalMountChange)
    ) {
      return;
    }

    if (allowDescriptionEdit) {
      onRename(trimmed, nextDescription, nextDefaultModel, nextLocalMounts);
    } else {
      onRename(trimmed, undefined, nextDefaultModel, nextLocalMounts);
    }
    onOpenChange(false);
  };

  const nativePickerSupported = supportsNativeDirectoryPicker();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-hidden sm:max-w-3xl">
        <form
          onSubmit={handleSubmit}
          className="flex max-h-[80vh] flex-col overflow-hidden"
        >
          <DialogHeader>
            <DialogTitle>{t("project.rename")}</DialogTitle>
          </DialogHeader>
          <div className="grid flex-1 gap-4 overflow-y-auto py-4 pr-1">
            <div className="grid gap-2">
              <Label htmlFor="project-name">{t("project.nameLabel")}</Label>
              <Input
                ref={inputRef}
                id="project-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t("project.namePlaceholder")}
                onKeyDown={(e) => {
                  if (e.key === "Escape") {
                    onOpenChange(false);
                  }
                }}
              />
            </div>
            {allowDescriptionEdit ? (
              <div className="grid gap-2">
                <Label htmlFor="project-description">
                  {t("project.descriptionLabel")}
                </Label>
                <Textarea
                  id="project-description"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder={t("project.detail.descriptionPlaceholder")}
                  rows={4}
                />
              </div>
            ) : null}

            <Collapsible
              open={advancedOpen}
              onOpenChange={setAdvancedOpen}
              className="rounded-2xl border border-border/60 bg-muted/20"
            >
              <CollapsibleTrigger asChild>
                <button
                  type="button"
                  className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">
                      {t("project.advanced.title")}
                    </p>
                  </div>
                  <ChevronDown
                    className="size-4 shrink-0 text-muted-foreground transition-transform data-[state=open]:rotate-180"
                    data-state={advancedOpen ? "open" : "closed"}
                  />
                </button>
              </CollapsibleTrigger>

              <CollapsibleContent className="border-t border-border/60 px-4 py-4">
                <div className="grid gap-4">
                  <div className="grid max-w-full gap-2 sm:max-w-[50%]">
                    <Label htmlFor="project-default-model">
                      {t("project.advanced.defaultModelLabel")}
                    </Label>
                    <div className="overflow-hidden rounded-xl border border-border bg-background">
                      <ModelSelector
                        options={modelOptions}
                        selection={modelSelection}
                        defaultSelection={defaultSelection}
                        fallbackLabel={
                          initialState.modelSelection?.modelId ||
                          t("project.advanced.defaultModelPlaceholder")
                        }
                        onChange={setModelSelection}
                        disabled={isLoadingModelCatalog}
                        triggerClassName="h-10 w-full rounded-none justify-between px-3"
                      />
                    </div>
                  </div>

                  <div className="rounded-xl border border-border/60 bg-background px-4 py-3">
                    <div className="min-w-0">
                      <div className="min-w-0">
                        <Label className="flex items-center gap-2 text-sm font-medium">
                          {t("project.advanced.mountTitle")}
                        </Label>
                        <p className="mt-1 text-xs text-muted-foreground">
                          {t("project.advanced.mountDescription")}
                        </p>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-4">
                      <LocalFilesystemModeSelector
                        mode={filesystemMode}
                        onModeChange={handleFilesystemModeChange}
                      />

                      {filesystemMode === "local_mount" ? (
                        <LocalMountEditor
                          rows={mountRows}
                          nativePickerSupported={nativePickerSupported}
                          onAddRow={() => {
                            void handleAddRow();
                          }}
                          onRemoveRow={handleRemoveRow}
                          onRowChange={handleRowChange}
                          idPrefix="project-mount"
                        />
                      ) : (
                        <div className="rounded-2xl border border-dashed border-border/60 bg-muted/20 p-4 text-sm text-muted-foreground">
                          {t("filesystem.messages.sandboxOnly")}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CollapsibleContent>
            </Collapsible>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {t("common.cancel")}
            </Button>
            <Button type="submit" disabled={!name.trim()}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
