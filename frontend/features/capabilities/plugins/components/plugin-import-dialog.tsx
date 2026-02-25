"use client";

import * as React from "react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { CheckCheck, ListChecks } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { useT } from "@/lib/i18n/client";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import type {
  PluginImportCandidate,
  PluginImportCommitResponse,
} from "@/features/capabilities/plugins/types";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";
import { playInstallSound } from "@/lib/utils/sound";

type SourceTab = "zip" | "github";

interface CandidateSelectionState {
  selected: boolean;
  nameOverride: string;
}

const CANDIDATES_PAGE_SIZE = 5;

export interface PluginImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported?: () => void | Promise<void>;
}

export function PluginImportDialog({
  open,
  onClose,
  onImported,
}: PluginImportDialogProps) {
  const { t } = useT("translation");
  const [tab, setTab] = useState<SourceTab>("github");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState("");

  const [archiveKey, setArchiveKey] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<PluginImportCandidate[]>([]);
  const [candidatePage, setCandidatePage] = useState(1);
  const [selections, setSelections] = useState<
    Record<string, CandidateSelectionState>
  >({});

  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitProgress, setCommitProgress] = useState<number | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitResult, setCommitResult] =
    useState<PluginImportCommitResponse | null>(null);

  const isActiveRef = React.useRef(true);
  React.useEffect(() => {
    isActiveRef.current = true;
    return () => {
      isActiveRef.current = false;
    };
  }, []);

  const reset = React.useCallback(() => {
    setTab("github");
    setZipFile(null);
    setGithubUrl("");
    setArchiveKey(null);
    setCandidates([]);
    setCandidatePage(1);
    setSelections({});
    setIsDiscovering(false);
    setIsCommitting(false);
    setCommitProgress(null);
    setCommitError(null);
    setCommitResult(null);
  }, []);

  const handleClose = React.useCallback(() => {
    onClose();
    setTimeout(reset, 0);
  }, [onClose, reset]);

  const selectedCandidates = useMemo(() => {
    return candidates.filter((c) => selections[c.relative_path]?.selected);
  }, [candidates, selections]);

  const totalCandidatePages = useMemo(() => {
    return Math.max(1, Math.ceil(candidates.length / CANDIDATES_PAGE_SIZE));
  }, [candidates.length]);

  React.useEffect(() => {
    setCandidatePage((prev) => Math.min(prev, totalCandidatePages));
  }, [totalCandidatePages]);

  const candidatePageClamped = useMemo(() => {
    return Math.min(candidatePage, totalCandidatePages);
  }, [candidatePage, totalCandidatePages]);

  const pagedCandidates = useMemo(() => {
    const start = (candidatePageClamped - 1) * CANDIDATES_PAGE_SIZE;
    return candidates.slice(start, start + CANDIDATES_PAGE_SIZE);
  }, [candidates, candidatePageClamped]);

  const isPageFullySelected = useMemo(() => {
    if (pagedCandidates.length === 0) return false;
    return pagedCandidates.every((c) => selections[c.relative_path]?.selected);
  }, [pagedCandidates, selections]);

  const isAllSelected = useMemo(() => {
    if (candidates.length === 0) return false;
    return candidates.every((c) => selections[c.relative_path]?.selected);
  }, [candidates, selections]);

  const overwriteCount = useMemo(() => {
    return selectedCandidates.filter((c) => c.will_overwrite).length;
  }, [selectedCandidates]);

  const canCommit = useMemo(() => {
    if (!archiveKey) return false;
    if (selectedCandidates.length === 0) return false;
    for (const c of selectedCandidates) {
      if (c.requires_name) {
        const name = selections[c.relative_path]?.nameOverride?.trim() || "";
        if (!name) return false;
      }
    }
    return true;
  }, [archiveKey, selectedCandidates, selections]);

  const onDiscover = async () => {
    setIsDiscovering(true);
    setCommitResult(null);
    setCommitError(null);
    try {
      const formData = new FormData();
      if (tab === "zip") {
        if (!zipFile) {
          toast.error(t("library.pluginsImport.toasts.missingZip"));
          return;
        }
        formData.append("file", zipFile);
      } else {
        const url = githubUrl.trim();
        if (!url) {
          toast.error(t("library.pluginsImport.toasts.missingGithubUrl"));
          return;
        }
        formData.append("github_url", url);
      }

      const resp = await pluginsService.importDiscover(formData);
      setArchiveKey(resp.archive_key);
      setCandidates(resp.candidates || []);
      setCandidatePage(1);

      const next: Record<string, CandidateSelectionState> = {};
      for (const c of resp.candidates || []) {
        next[c.relative_path] = {
          selected: true,
          nameOverride: "",
        };
      }
      setSelections(next);

      toast.success(t("library.pluginsImport.toasts.discovered"));
    } catch (error) {
      console.error("[PluginsImport] discover failed:", error);
      toast.error(t("library.pluginsImport.toasts.discoverError"));
    } finally {
      setIsDiscovering(false);
    }
  };

  const onCommit = async () => {
    if (!archiveKey) return;
    if (!canCommit) return;

    setIsCommitting(true);
    setCommitError(null);
    setCommitResult(null);
    setCommitProgress(0);
    try {
      const payload = {
        archive_key: archiveKey,
        selections: selectedCandidates.map((c) => ({
          relative_path: c.relative_path,
          name_override: c.requires_name
            ? selections[c.relative_path]?.nameOverride?.trim() || null
            : null,
        })),
      };

      const enqueue = await pluginsService.importCommit(payload);

      const startedAt = Date.now();
      let finalError: string | null = null;
      let finalResult: PluginImportCommitResponse | null = null;
      while (true) {
        if (!isActiveRef.current) return;

        const job = await pluginsService.getImportJob(enqueue.job_id);
        if (!isActiveRef.current) return;

        setCommitProgress(typeof job.progress === "number" ? job.progress : 0);

        if (job.status === "success") {
          finalResult = job.result;
          setCommitResult(job.result);
          break;
        }

        if (job.status === "failed") {
          finalError = job.error || "";
          finalResult = job.result;
          setCommitError(finalError);
          setCommitResult(job.result);
          break;
        }

        if (Date.now() - startedAt > 10 * 60 * 1000) {
          finalError = t("library.pluginsImport.toasts.commitTimeout");
          setCommitError(finalError);
          break;
        }

        await new Promise((resolve) => setTimeout(resolve, 1000));
      }

      if (!isActiveRef.current) return;

      if (finalError) {
        toast.error(
          finalError || t("library.pluginsImport.toasts.commitError"),
        );
        return;
      }

      const failed = (finalResult?.items || []).filter(
        (i) => i.status !== "success",
      );
      if (failed.length > 0) {
        toast.error(t("library.pluginsImport.toasts.partialFailed"));
        return;
      }

      toast.success(t("library.pluginsImport.toasts.committed"));
      playInstallSound();
      await onImported?.();
      handleClose();
    } catch (error) {
      console.error("[PluginsImport] commit failed:", error);
      toast.error(t("library.pluginsImport.toasts.commitError"));
    } finally {
      setIsCommitting(false);
    }
  };

  const toggleSelectAll = (checked: boolean) => {
    const next: Record<string, CandidateSelectionState> = { ...selections };
    for (const c of candidates) {
      next[c.relative_path] = {
        selected: checked,
        nameOverride: next[c.relative_path]?.nameOverride || "",
      };
    }
    setSelections(next);
  };

  const toggleSelectPage = (checked: boolean) => {
    const next: Record<string, CandidateSelectionState> = { ...selections };
    for (const c of pagedCandidates) {
      next[c.relative_path] = {
        selected: checked,
        nameOverride: next[c.relative_path]?.nameOverride || "",
      };
    }
    setSelections(next);
  };

  const toggleCandidate = (relativePath: string, checked: boolean) => {
    setSelections((prev) => ({
      ...prev,
      [relativePath]: {
        selected: checked,
        nameOverride: prev[relativePath]?.nameOverride || "",
      },
    }));
  };

  const updateNameOverride = (relativePath: string, value: string) => {
    setSelections((prev) => ({
      ...prev,
      [relativePath]: {
        selected: prev[relativePath]?.selected ?? true,
        nameOverride: value,
      },
    }));
  };

  const hasPreview = candidates.length > 0 && !!archiveKey;
  const selectionDisabled = isCommitting || isDiscovering;
  const pageSelectionTitle = isPageFullySelected
    ? t("library.pluginsImport.preview.selection.clearPage")
    : t("library.pluginsImport.preview.selection.selectPage");
  const allSelectionTitle = isAllSelected
    ? t("library.pluginsImport.preview.selection.clearAll")
    : t("library.pluginsImport.preview.selection.selectAll");

  return (
    <Dialog open={open} onOpenChange={(v) => !v && handleClose()}>
      <CapabilityDialogContent
        title={t("library.pluginsImport.title")}
        description={t("library.pluginsImport.description")}
        maxWidth="35rem"
        maxHeight="45dvh"
        desktopMaxHeight="45dvh"
        className="h-[45dvh]"
        bodyClassName="space-y-6 bg-background px-6 pt-4 pb-6"
        footer={
          <DialogFooter className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isCommitting}
              className="w-full"
            >
              {t("common.cancel")}
            </Button>
            {!hasPreview ? (
              <Button
                onClick={onDiscover}
                disabled={isDiscovering}
                className="w-full"
              >
                {isDiscovering
                  ? t("library.pluginsImport.actions.discovering")
                  : t("library.pluginsImport.actions.discover")}
              </Button>
            ) : (
              <Button
                onClick={onCommit}
                disabled={!canCommit || isCommitting}
                className={
                  isCommitting
                    ? "relative w-full overflow-hidden !bg-primary/50 text-primary-foreground hover:!bg-primary/50"
                    : "w-full"
                }
                aria-busy={isCommitting}
                aria-valuenow={isCommitting ? (commitProgress ?? 0) : undefined}
                aria-valuemin={isCommitting ? 0 : undefined}
                aria-valuemax={isCommitting ? 100 : undefined}
              >
                {isCommitting && (
                  <span
                    className="absolute inset-y-0 left-0 bg-primary transition-[width] duration-300 ease-out"
                    style={{
                      width: `${typeof commitProgress === "number" ? commitProgress : 0}%`,
                    }}
                    aria-hidden
                  />
                )}
                <span
                  className={
                    isCommitting
                      ? "relative z-10 text-primary-foreground"
                      : undefined
                  }
                >
                  {isCommitting
                    ? t("library.pluginsImport.actions.committing")
                    : t("library.pluginsImport.actions.commit")}
                </span>
              </Button>
            )}
          </DialogFooter>
        }
      >
        <div className="space-y-6">
          {!hasPreview && (
            <Tabs
              value={tab}
              onValueChange={(v) => setTab(v as SourceTab)}
              className="gap-4"
            >
              <TabsList className="p-1 transition-colors duration-200">
                <TabsTrigger
                  value="github"
                  className="data-[state=inactive]:scale-[0.98]"
                >
                  {t("library.pluginsImport.tabs.github")}
                </TabsTrigger>
                <TabsTrigger
                  value="zip"
                  className="data-[state=inactive]:scale-[0.98]"
                >
                  {t("library.pluginsImport.tabs.zip")}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="zip" className="space-y-3">
                <Input
                  type="file"
                  accept=".zip"
                  onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                  className="text-muted-foreground/80 placeholder:text-muted-foreground/50 file:text-muted-foreground/80"
                />
                {zipFile && (
                  <div className="text-xs text-muted-foreground/60">
                    {zipFile.name} ({Math.round(zipFile.size / 1024)} KB)
                  </div>
                )}
              </TabsContent>

              <TabsContent value="github" className="space-y-3">
                <Input
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder={t(
                    "library.pluginsImport.placeholders.githubUrl",
                  )}
                  className="text-muted-foreground/80 placeholder:text-muted-foreground/50"
                />
                <div className="text-xs text-muted-foreground/60">
                  {t("library.pluginsImport.hints.github")}
                </div>
              </TabsContent>
            </Tabs>
          )}

          {hasPreview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm text-muted-foreground">
                  {t("library.pluginsImport.preview.found")}{" "}
                  <span className="text-foreground font-medium">
                    {candidates.length}
                  </span>{" "}
                  {t("library.pluginsImport.preview.items")}
                  {overwriteCount > 0 && (
                    <span className="ml-2">
                      · {t("library.pluginsImport.preview.overwrite")}{" "}
                      <span className="text-foreground font-medium">
                        {overwriteCount}
                      </span>{" "}
                      {t("library.pluginsImport.preview.overwriteItems")}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    disabled={selectionDisabled || pagedCandidates.length === 0}
                    onClick={() => toggleSelectPage(!isPageFullySelected)}
                    title={pageSelectionTitle}
                    aria-label={pageSelectionTitle}
                    className={
                      isPageFullySelected
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }
                  >
                    <ListChecks className="size-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    disabled={selectionDisabled || candidates.length === 0}
                    onClick={() => toggleSelectAll(!isAllSelected)}
                    title={allSelectionTitle}
                    aria-label={allSelectionTitle}
                    className={
                      isAllSelected
                        ? "text-foreground"
                        : "text-muted-foreground"
                    }
                  >
                    <CheckCheck className="size-4" />
                  </Button>
                </div>
              </div>

              <div className="space-y-2">
                {pagedCandidates.map((c) => {
                  const state = selections[c.relative_path] || {
                    selected: false,
                    nameOverride: "",
                  };
                  const displayName = c.plugin_name || c.relative_path;
                  return (
                    <div
                      key={c.relative_path}
                      role="button"
                      tabIndex={0}
                      className="flex items-start gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-3 cursor-pointer transition-colors hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
                      onClick={(e) => {
                        if (selectionDisabled) return;
                        if ((e.target as HTMLElement).closest("input")) return;
                        toggleCandidate(c.relative_path, !state.selected);
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          if (!selectionDisabled)
                            toggleCandidate(c.relative_path, !state.selected);
                        }
                      }}
                    >
                      <span onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          className="self-center"
                          checked={state.selected}
                          disabled={selectionDisabled}
                          onCheckedChange={(v) =>
                            toggleCandidate(c.relative_path, Boolean(v))
                          }
                        />
                      </span>
                      <div className="min-w-0 flex-1 space-y-2">
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-medium truncate">
                            {displayName}
                            {c.version && (
                              <span className="ml-1.5 font-normal text-muted-foreground">
                                v{c.version}
                              </span>
                            )}
                          </span>
                          {c.will_overwrite && (
                            <Badge
                              variant="outline"
                              className="shrink-0 text-xs"
                            >
                              {t("library.pluginsImport.preview.willOverwrite")}
                            </Badge>
                          )}
                        </div>
                        {c.description && (
                          <div className="text-xs text-muted-foreground line-clamp-2">
                            {c.description}
                          </div>
                        )}
                        {c.requires_name && state.selected && (
                          <div
                            className="space-y-1 pt-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Label className="text-xs">
                              {t("library.pluginsImport.fields.nameOverride")}
                            </Label>
                            <Input
                              className="h-8 text-xs"
                              value={state.nameOverride}
                              onChange={(e) =>
                                updateNameOverride(
                                  c.relative_path,
                                  e.target.value,
                                )
                              }
                              placeholder={t(
                                "library.pluginsImport.placeholders.name",
                              )}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {totalCandidatePages > 1 && (
                <div className="flex items-center justify-between gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={candidatePageClamped <= 1}
                    onClick={() => setCandidatePage((p) => Math.max(1, p - 1))}
                  >
                    {t("library.pluginsImport.preview.pagination.prev")}
                  </Button>
                  <div className="text-xs text-muted-foreground">
                    {t("library.pluginsImport.preview.pagination.page", {
                      page: candidatePageClamped,
                      pages: totalCandidatePages,
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={candidatePageClamped >= totalCandidatePages}
                    onClick={() =>
                      setCandidatePage((p) =>
                        Math.min(totalCandidatePages, p + 1),
                      )
                    }
                  >
                    {t("library.pluginsImport.preview.pagination.next")}
                  </Button>
                </div>
              )}

              {commitResult && (
                <div className="rounded-xl border border-border/50 bg-muted/5 px-4 py-3 space-y-2">
                  <div className="text-sm font-medium">
                    {t("library.pluginsImport.result.title")}
                  </div>
                  <div className="space-y-1">
                    {(commitResult.items || []).map((item) => (
                      <div
                        key={item.relative_path}
                        className="text-xs text-muted-foreground flex items-center justify-between gap-2"
                      >
                        <span className="font-mono truncate">
                          {item.plugin_name || item.relative_path}
                        </span>
                        <span className="shrink-0">
                          {item.status === "success"
                            ? t("library.pluginsImport.result.success")
                            : t("library.pluginsImport.result.failed")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {commitError && !isCommitting && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 space-y-1">
                  <div className="text-sm font-medium">
                    {t("library.pluginsImport.result.failed")}
                  </div>
                  <div className="text-xs text-muted-foreground break-words">
                    {commitError}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </CapabilityDialogContent>
    </Dialog>
  );
}
