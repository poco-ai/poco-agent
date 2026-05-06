"use client";

import * as React from "react";
import {
  AlignLeft,
  FolderTree,
  Loader2,
  PencilLine,
  Sparkles,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";
import { ApiError } from "@/lib/errors";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import type { Skill } from "@/features/capabilities/skills/types";
import type { SkillUpdateInput } from "@/features/capabilities/skills/types";
import { DocumentViewer, FileSidebar, type FileNode } from "@/features/chat";

interface SkillSettingsDialogProps {
  skill: Skill | null;
  skills: Skill[];
  open: boolean;
  onClose: () => void;
  onSaved?: (skill: Skill) => Promise<void> | void;
  onSaveSkill?: (
    skillId: number,
    input: SkillUpdateInput,
  ) => Promise<Skill | void>;
  onDeleteSkill?: (skillId: number) => Promise<void> | void;
  allowSystemEdit?: boolean;
  showPolicyControls?: boolean;
  loadSkillFiles?: (skillId: number) => Promise<FileNode[]>;
}

function flattenFiles(nodes: FileNode[]): FileNode[] {
  const result: FileNode[] = [];

  const visit = (items: FileNode[]) => {
    for (const item of items) {
      if (item.type === "file") {
        result.push(item);
        continue;
      }
      if (item.children?.length) {
        visit(item.children);
      }
    }
  };

  visit(nodes);
  return result;
}

function findPreferredFile(
  nodes: FileNode[],
  preferredPath?: string,
): FileNode | undefined {
  const flatFiles = flattenFiles(nodes);
  return (
    (preferredPath
      ? flatFiles.find((file) => file.path === preferredPath)
      : undefined) ?? flatFiles[0]
  );
}

function getEntryS3Key(skill: Skill | null): string | null {
  if (!skill || !skill.entry || typeof skill.entry !== "object") {
    return null;
  }

  const rawValue = skill.entry.s3_key ?? skill.entry.key ?? null;
  return typeof rawValue === "string" && rawValue.trim() ? rawValue : null;
}

function getSourceLabel(skill: Skill, t: (key: string) => string): string {
  const kind = skill.source?.kind ?? "unknown";

  if (kind === "system") {
    return t("library.skillSettings.source.system");
  }
  if (kind === "skill-creator") {
    return t("library.skillsManager.source.skillCreator");
  }
  if (kind === "github") {
    const repo = skill.source?.repo?.trim();
    return repo || t("library.skillSettings.source.github");
  }
  if (kind === "zip") {
    const filename = skill.source?.filename?.trim();
    return filename || t("library.skillSettings.source.zip");
  }
  if (kind === "manual") {
    return t("library.skillSettings.source.manual");
  }
  if (kind === "marketplace") {
    const market = skill.source?.market?.trim();
    if (market === "skillsmp") {
      return t("library.skillSettings.source.skillsmp");
    }
    return t("library.skillSettings.source.marketplace");
  }

  return t("library.skillSettings.source.unknown");
}

export function SkillSettingsDialog({
  skill,
  skills,
  open,
  onClose,
  onSaved,
  onSaveSkill,
  onDeleteSkill,
  allowSystemEdit = false,
  showPolicyControls = false,
  loadSkillFiles,
}: SkillSettingsDialogProps) {
  const { t } = useT("translation");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [files, setFiles] = React.useState<FileNode[]>([]);
  const [selectedFile, setSelectedFile] = React.useState<FileNode>();
  const [isLoadingFiles, setIsLoadingFiles] = React.useState(false);
  const [isPreviewVisible, setIsPreviewVisible] = React.useState(false);
  const [isSaving, setIsSaving] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [saveError, setSaveError] = React.useState<string | null>(null);
  const [defaultEnabled, setDefaultEnabled] = React.useState(false);
  const [forceEnabled, setForceEnabled] = React.useState(false);
  const [adminDisabled, setAdminDisabled] = React.useState(false);
  const loadSkillFilesApi = React.useCallback(
    (skillId: number) =>
      loadSkillFiles
        ? loadSkillFiles(skillId)
        : skillsService.listSkillFiles(skillId),
    [loadSkillFiles],
  );

  const isSystemSkill = skill?.scope === "system";
  const isSystemReadonly = Boolean(isSystemSkill && !allowSystemEdit);
  const isBuiltinSkill = Boolean(skill?.is_builtin);
  const isMetadataReadonly = isSystemReadonly || isBuiltinSkill;
  const trimmedName = name.trim();
  const trimmedDescription = description.trim();
  const storagePath = getEntryS3Key(skill);
  const nameConflict = React.useMemo(() => {
    if (!skill || !trimmedName) {
      return false;
    }

    const normalizedName = trimmedName.toLowerCase();
    return skills.some(
      (item) =>
        item.id !== skill.id &&
        item.name.trim().toLowerCase() === normalizedName,
    );
  }, [skill, skills, trimmedName]);

  const hasChanges = React.useMemo(() => {
    if (!skill) {
      return false;
    }

    return (
      trimmedName !== skill.name ||
      trimmedDescription !== (skill.description ?? "") ||
      (showPolicyControls &&
        (defaultEnabled !== skill.default_enabled ||
          forceEnabled !== skill.force_enabled ||
          adminDisabled !== skill.admin_disabled))
    );
  }, [
    adminDisabled,
    defaultEnabled,
    forceEnabled,
    showPolicyControls,
    skill,
    trimmedDescription,
    trimmedName,
  ]);

  const refreshFiles = React.useCallback(
    async (preferredPath?: string): Promise<FileNode[]> => {
      if (!skill) {
        setFiles([]);
        setSelectedFile(undefined);
        return [];
      }

      const nextFiles = await loadSkillFilesApi(skill.id);
      setFiles(nextFiles);
      setSelectedFile(findPreferredFile(nextFiles, preferredPath));
      return nextFiles;
    },
    [loadSkillFilesApi, skill],
  );

  React.useEffect(() => {
    if (!skill) {
      setName("");
      setDescription("");
      setSaveError(null);
      return;
    }

    setName(skill.name);
    setDescription(skill.description ?? "");
    setDefaultEnabled(skill.default_enabled);
    setForceEnabled(skill.force_enabled);
    setAdminDisabled(skill.admin_disabled);
    setSaveError(null);
    setIsSaving(false);
    setIsPreviewVisible(false);
  }, [skill]);

  React.useEffect(() => {
    if (!open || !skill) {
      setFiles([]);
      setSelectedFile(undefined);
      setIsLoadingFiles(false);
      return;
    }

    let cancelled = false;

    const loadFiles = async () => {
      try {
        setIsLoadingFiles(true);
        const nextFiles = await loadSkillFilesApi(skill.id);
        if (cancelled) {
          return;
        }
        setFiles(nextFiles);
        setSelectedFile(findPreferredFile(nextFiles));
      } catch (error) {
        console.error(
          "[SkillSettingsDialog] Failed to load skill files",
          error,
        );
        if (!cancelled) {
          setFiles([]);
          setSelectedFile(undefined);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingFiles(false);
        }
      }
    };

    void loadFiles();

    return () => {
      cancelled = true;
    };
  }, [loadSkillFilesApi, open, skill]);

  React.useEffect(() => {
    if (!isPreviewVisible) {
      return;
    }

    const handleClosePreview = () => {
      setIsPreviewVisible(false);
    };

    window.addEventListener("close-document-viewer", handleClosePreview);
    return () => {
      window.removeEventListener("close-document-viewer", handleClosePreview);
    };
  }, [isPreviewVisible]);

  const handleSave = async () => {
    if (
      !skill ||
      isSystemReadonly ||
      !trimmedName ||
      nameConflict ||
      !hasChanges
    ) {
      return;
    }

    setSaveError(null);
    setIsSaving(true);
    try {
      const saveSkill = onSaveSkill ?? skillsService.updateSkill;
      const updated = await saveSkill(skill.id, {
        name: isMetadataReadonly ? skill.name : trimmedName,
        description: isMetadataReadonly
          ? skill.description
          : trimmedDescription || null,
        default_enabled: showPolicyControls ? defaultEnabled : undefined,
        force_enabled: showPolicyControls ? forceEnabled : undefined,
        admin_disabled: showPolicyControls ? adminDisabled : undefined,
      });
      const nextSkill = updated ?? {
        ...skill,
        name: isMetadataReadonly ? skill.name : trimmedName,
        description: isMetadataReadonly
          ? skill.description
          : trimmedDescription || null,
        default_enabled: showPolicyControls
          ? defaultEnabled
          : skill.default_enabled,
        force_enabled: showPolicyControls ? forceEnabled : skill.force_enabled,
        admin_disabled: showPolicyControls
          ? adminDisabled
          : skill.admin_disabled,
      };
      toast.success(t("library.skillSettings.toasts.saved"));
      await onSaved?.(nextSkill);
      onClose();
    } catch (error) {
      console.error("[SkillSettingsDialog] Failed to save skill", error);
      const message =
        error instanceof ApiError && error.message.trim()
          ? error.message
          : t("library.skillSettings.toasts.saveFailed");
      setSaveError(message);
      toast.error(message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!skill || !onDeleteSkill || isSaving || isDeleting) {
      return;
    }

    setSaveError(null);
    setIsDeleting(true);
    try {
      await onDeleteSkill(skill.id);
      toast.success(t("common.deleted"));
      onClose();
    } catch (error) {
      console.error("[SkillSettingsDialog] Failed to delete skill", error);
      const message =
        error instanceof ApiError && error.message.trim()
          ? error.message
          : t("library.skillSettings.toasts.saveFailed");
      setSaveError(message);
      toast.error(message);
    } finally {
      setIsDeleting(false);
    }
  };

  const ensureFreshFile = React.useCallback(
    async (file: FileNode): Promise<FileNode | undefined> => {
      try {
        const nextFiles = await refreshFiles(file.path);
        return findPreferredFile(nextFiles, file.path) ?? file;
      } catch (error) {
        console.error(
          "[SkillSettingsDialog] Failed to refresh skill file URL",
          error,
        );
        return file;
      }
    },
    [refreshFiles],
  );

  if (!skill) {
    return null;
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => !nextOpen && onClose()}>
      <DialogContent
        className="max-h-[90vh] w-[calc(100vw-2rem)] overflow-hidden border-0  p-0 shadow-none sm:max-w-[90vw] lg:max-w-[960px] xl:max-w-[1000px]"
        showCloseButton={false}
      >
        <DialogTitle className="sr-only">{skill.name}</DialogTitle>
        <DialogDescription className="sr-only">
          {t("library.skillSettings.title")}
        </DialogDescription>

        <div className="flex flex-col overflow-visible rounded-lg border border-border bg-card/70 p-4 shadow-sm md:h-[60vh] md:max-h-[80vh] md:overflow-hidden">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 space-y-1">
              <div className="flex items-center gap-2">
                <div className="flex size-8 items-center justify-center rounded-full bg-primary/10 text-primary">
                  <Sparkles className="size-4" />
                </div>
                <div className="flex min-w-0 flex-wrap items-center gap-2">
                  <div className="truncate text-sm font-medium text-foreground">
                    {skill.name}
                  </div>
                  <Badge
                    variant="outline"
                    className="text-xs text-muted-foreground"
                  >
                    {isSystemSkill
                      ? t("library.skillsManager.scope.system")
                      : t("library.skillsManager.scope.user")}
                  </Badge>
                  <Badge variant="secondary" className="text-xs">
                    {getSourceLabel(skill, t)}
                  </Badge>
                  {skill.admin_disabled ? (
                    <Badge variant="outline" className="text-xs">
                      {t("common.disabled")}
                    </Badge>
                  ) : null}
                </div>
              </div>
            </div>
            {isSaving ? (
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            ) : null}
          </div>

          <div className="mt-4 grid gap-4 md:min-h-0 md:flex-1 md:grid-cols-[minmax(200px,0.6fr)_minmax(0,1.5fr)] md:overflow-hidden">
            <div className="min-h-[220px] overflow-hidden rounded-lg border border-border/60 bg-background md:min-h-0">
              {isLoadingFiles ? (
                <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-muted-foreground">
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  {t("library.skillSettings.loadingFiles")}
                </div>
              ) : files.length === 0 ? (
                <div className="flex h-full min-h-[320px] items-center justify-center px-4 text-center text-sm text-muted-foreground">
                  {t("library.skillSettings.emptyFiles")}
                </div>
              ) : (
                <FileSidebar
                  files={files}
                  onFileSelect={(file) => {
                    setSelectedFile(file);
                    setIsPreviewVisible(true);
                  }}
                  selectedFile={selectedFile}
                  embedded
                />
              )}
            </div>

            <div
              className={cn(
                "min-h-[320px] overflow-hidden rounded-lg bg-background md:min-h-0",
                isPreviewVisible && selectedFile
                  ? "bg-transparent"
                  : "border border-border/60",
              )}
            >
              {isPreviewVisible && selectedFile ? (
                <div className="h-[60vh] min-h-[360px] overflow-hidden md:h-full md:min-h-0">
                  <DocumentViewer
                    file={selectedFile}
                    ensureFreshFile={ensureFreshFile}
                  />
                </div>
              ) : (
                <div className="space-y-4 p-4 md:min-h-0 md:overflow-y-auto">
                  <div className="space-y-2">
                    <Label className="flex items-center gap-2">
                      <PencilLine className="size-4 text-muted-foreground" />
                      {t("library.skillSettings.nameLabel")}
                    </Label>
                    <Input
                      value={name}
                      disabled={isMetadataReadonly || isSaving}
                      onChange={(event) => {
                        setName(event.target.value);
                        if (saveError) {
                          setSaveError(null);
                        }
                      }}
                      placeholder={t("library.skillSettings.namePlaceholder")}
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      <AlignLeft className="size-4" />
                      {t("library.skillSettings.descriptionLabel")}
                    </div>
                    <Textarea
                      value={description}
                      disabled={isMetadataReadonly || isSaving}
                      onChange={(event) => {
                        setDescription(event.target.value);
                        if (saveError) {
                          setSaveError(null);
                        }
                      }}
                      placeholder={t(
                        "library.skillSettings.descriptionPlaceholder",
                      )}
                      className="min-h-28  max-h-36 resize-y overflow-y-auto"
                    />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      <FolderTree className="size-4" />
                      {t("library.skillSettings.storagePathLabel")}
                    </div>
                    <code className="block rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-xs text-muted-foreground">
                      {storagePath ||
                        t("library.skillSettings.storagePathUnavailable")}
                    </code>
                  </div>

                  {isMetadataReadonly ? (
                    <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2 text-sm text-muted-foreground">
                      {t("library.skillSettings.readonlyHint")}
                    </div>
                  ) : null}

                  {nameConflict ? (
                    <div className="rounded-md border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-700 dark:text-amber-300">
                      <div className="flex items-start gap-2">
                        <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                        <div>{t("library.skillSettings.nameConflict")}</div>
                      </div>
                    </div>
                  ) : null}

                  {showPolicyControls ? (
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="space-y-2">
                        <Label>
                          {t("settings.admin.policyDefaultEnabled")}
                        </Label>
                        <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                          <Switch
                            checked={defaultEnabled}
                            onCheckedChange={setDefaultEnabled}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>{t("settings.admin.policyForceEnabled")}</Label>
                        <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                          <Switch
                            checked={forceEnabled}
                            onCheckedChange={setForceEnabled}
                          />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label>
                          {t("settings.admin.policyDisabledForUsers")}
                        </Label>
                        <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
                          <Switch
                            checked={adminDisabled}
                            onCheckedChange={setAdminDisabled}
                          />
                        </div>
                      </div>
                    </div>
                  ) : null}

                  {saveError ? (
                    <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                      {saveError}
                    </div>
                  ) : null}
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 flex items-center justify-end gap-2">
            {onDeleteSkill && !skill.is_builtin ? (
              <Button
                variant="destructive"
                disabled={isSaving || isDeleting}
                onClick={handleDelete}
                className="mr-auto"
              >
                {isDeleting ? (
                  <>
                    <Loader2 className="mr-2 size-4 animate-spin" />
                    {t("common.deleting")}
                  </>
                ) : (
                  <>
                    <Trash2 className="mr-2 size-4" />
                    {t("common.delete")}
                  </>
                )}
              </Button>
            ) : null}
            <Button variant="outline" disabled={isSaving} onClick={onClose}>
              {t("common.cancel")}
            </Button>
            <Button
              disabled={
                isSaving ||
                isDeleting ||
                isSystemReadonly ||
                !trimmedName ||
                nameConflict ||
                !hasChanges
              }
              onClick={handleSave}
            >
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 size-4 animate-spin" />
                  {t("common.saving")}
                </>
              ) : (
                t("common.save")
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
