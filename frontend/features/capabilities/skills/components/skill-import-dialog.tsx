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
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import type {
  SkillImportCandidate,
  SkillImportCommitResponse,
} from "@/features/capabilities/skills/types";
import { CapabilityDialogContent } from "@/features/capabilities/components/capability-dialog-content";
import { playInstallSound } from "@/lib/utils/sound";

type SourceTab = "zip" | "github" | "command";

interface CandidateSelectionState {
  selected: boolean;
  nameOverride: string;
}

const CANDIDATES_PAGE_SIZE = 5;
const GITHUB_URL_PATTERN = /https?:\/\/github\.com\/[^\s'"]+/i;
const SKILL_ARG_PATTERN =
  /(?:^|\s)--skill(?:=|\s+)(?:"([^"]+)"|'([^']+)'|([^\s]+))/i;

interface ParsedSkillImportInput {
  githubUrl: string | null;
  requestedSkill: string | null;
}

function parseSkillImportInput(
  rawInput: string,
): ParsedSkillImportInput | null {
  const input = rawInput.trim();
  if (!input) return null;

  const githubUrlMatch = input.match(GITHUB_URL_PATTERN);
  const githubUrl = (githubUrlMatch?.[0] ?? "").trim();

  const skillArgMatch = input.match(SKILL_ARG_PATTERN);
  const requestedSkill = (
    skillArgMatch?.[1] ??
    skillArgMatch?.[2] ??
    skillArgMatch?.[3] ??
    ""
  ).trim();

  return {
    githubUrl: githubUrl || null,
    requestedSkill: requestedSkill || null,
  };
}

export interface SkillImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImported?: () => void | Promise<void>;
}

export function SkillImportDialog({
  open,
  onClose,
  onImported,
}: SkillImportDialogProps) {
  const { t } = useT("translation");
  const [tab, setTab] = useState<SourceTab>("github");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [commandInput, setCommandInput] = useState("");

  const [archiveKey, setArchiveKey] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<SkillImportCandidate[]>([]);
  const [candidatePage, setCandidatePage] = useState(1);
  const [selections, setSelections] = useState<
    Record<string, CandidateSelectionState>
  >({});

  const [isDiscovering, setIsDiscovering] = useState(false);
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitProgress, setCommitProgress] = useState<number | null>(null);
  const [commitError, setCommitError] = useState<string | null>(null);
  const [commitResult, setCommitResult] =
    useState<SkillImportCommitResponse | null>(null);

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
    setCommandInput("");
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
    // Reset state after close so the dialog animation is not affected.
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
      const parsedGithubInput =
        tab === "github" ? parseSkillImportInput(githubUrl) : null;
      const parsedCommandInput =
        tab === "command" ? parseSkillImportInput(commandInput) : null;
      if (tab === "zip") {
        if (!zipFile) {
          toast.error(t("library.skillsImport.toasts.missingZip"));
          return;
        }
        formData.append("file", zipFile);
      } else if (tab === "command") {
        if (!parsedCommandInput?.githubUrl) {
          toast.error(t("library.skillsImport.toasts.invalidCommand"));
          return;
        }
        formData.append("github_url", parsedCommandInput.githubUrl);
      } else {
        const url = parsedGithubInput?.githubUrl ?? githubUrl.trim();
        if (!url) {
          toast.error(t("library.skillsImport.toasts.missingGithubUrl"));
          return;
        }
        formData.append("github_url", url);
      }

      const resp = await skillsService.importDiscover(formData);
      setArchiveKey(resp.archive_key);
      setCandidates(resp.candidates || []);
      setCandidatePage(1);

      const requestedSkillRaw =
        tab === "github"
          ? parsedGithubInput?.requestedSkill || null
          : tab === "command"
            ? parsedCommandInput?.requestedSkill || null
            : null;
      const requestedSkill = requestedSkillRaw?.toLowerCase() || null;
      const next: Record<string, CandidateSelectionState> = {};
      let hasRequestedSkillMatch = false;
      let matchedCandidatePage: number | null = null;
      for (const c of resp.candidates || []) {
        const candidateName = (c.skill_name || "").toLowerCase();
        const relativePath = c.relative_path.toLowerCase();
        const relativePathLeaf =
          c.relative_path === "."
            ? ""
            : c.relative_path.split("/").at(-1)?.toLowerCase() || "";
        const isRequested =
          !!requestedSkill &&
          (candidateName === requestedSkill ||
            relativePath === requestedSkill ||
            relativePathLeaf === requestedSkill);
        hasRequestedSkillMatch = hasRequestedSkillMatch || isRequested;
        next[c.relative_path] = {
          selected: requestedSkill ? isRequested : true,
          nameOverride:
            isRequested && c.requires_name ? requestedSkillRaw || "" : "",
        };
      }

      if (
        requestedSkill &&
        !hasRequestedSkillMatch &&
        (resp.candidates || []).length === 1 &&
        (resp.candidates || [])[0].requires_name
      ) {
        const rootCandidate = (resp.candidates || [])[0];
        next[rootCandidate.relative_path] = {
          selected: true,
          nameOverride: requestedSkillRaw || "",
        };
      }

      if (requestedSkill) {
        const matchedIndex = (resp.candidates || []).findIndex(
          (candidate) => next[candidate.relative_path]?.selected,
        );
        if (matchedIndex >= 0) {
          matchedCandidatePage =
            Math.floor(matchedIndex / CANDIDATES_PAGE_SIZE) + 1;
        }
      }

      if (matchedCandidatePage) {
        setCandidatePage(matchedCandidatePage);
      }
      setSelections(next);

      toast.success(t("library.skillsImport.toasts.discovered"));
    } catch (error) {
      console.error("[SkillsImport] discover failed:", error);
      toast.error(t("library.skillsImport.toasts.discoverError"));
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

      const enqueue = await skillsService.importCommit(payload);

      const startedAt = Date.now();
      let finalError: string | null = null;
      let finalResult: SkillImportCommitResponse | null = null;
      while (true) {
        if (!isActiveRef.current) return;

        const job = await skillsService.getImportJob(enqueue.job_id);
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

        // Safety net: avoid polling forever if something goes wrong.
        if (Date.now() - startedAt > 10 * 60 * 1000) {
          finalError = t("library.skillsImport.toasts.commitTimeout");
          setCommitError(finalError);
          break;
        }

        await new Promise((resolve) => setTimeout(resolve, 1000));
      }

      if (!isActiveRef.current) return;

      if (finalError) {
        toast.error(finalError || t("library.skillsImport.toasts.commitError"));
        return;
      }

      const failed = (finalResult?.items || []).filter(
        (i) => i.status !== "success",
      );
      if (failed.length > 0) {
        toast.error(t("library.skillsImport.toasts.partialFailed"));
        return;
      }

      toast.success(t("library.skillsImport.toasts.committed"));
      playInstallSound();
      await onImported?.();
      handleClose();
    } catch (error) {
      console.error("[SkillsImport] commit failed:", error);
      toast.error(t("library.skillsImport.toasts.commitError"));
    } finally {
      setIsCommitting(false);
    }
  };

  const hasPreview = candidates.length > 0 && !!archiveKey;
  const selectionDisabled = isCommitting || isDiscovering;
  const pageSelectionTitle = isPageFullySelected
    ? t("library.skillsImport.preview.selection.clearPage")
    : t("library.skillsImport.preview.selection.selectPage");
  const allSelectionTitle = isAllSelected
    ? t("library.skillsImport.preview.selection.clearAll")
    : t("library.skillsImport.preview.selection.selectAll");

  return (
    <Dialog open={open} onOpenChange={(open) => !open && handleClose()}>
      <CapabilityDialogContent
        title={t("library.skillsImport.title")}
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
                  ? t("library.skillsImport.actions.discovering")
                  : t("library.skillsImport.actions.discover")}
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
                    ? t("library.skillsImport.actions.committing")
                    : t("library.skillsImport.actions.commit")}
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
                  {t("library.skillsImport.tabs.github")}
                </TabsTrigger>
                <TabsTrigger
                  value="command"
                  className="data-[state=inactive]:scale-[0.98]"
                >
                  {t("library.skillsImport.tabs.command")}
                </TabsTrigger>
                <TabsTrigger
                  value="zip"
                  className="data-[state=inactive]:scale-[0.98]"
                >
                  {t("library.skillsImport.tabs.zip")}
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
                  placeholder={t("library.skillsImport.placeholders.githubUrl")}
                  className="text-muted-foreground/80 placeholder:text-muted-foreground/50"
                />
                <div className="text-xs text-muted-foreground/60">
                  {t("library.skillsImport.hints.github")}
                </div>
              </TabsContent>

              <TabsContent value="command" className="space-y-3">
                <Input
                  value={commandInput}
                  onChange={(e) => setCommandInput(e.target.value)}
                  placeholder={t("library.skillsImport.placeholders.command")}
                  className="text-muted-foreground/80 placeholder:text-muted-foreground/50"
                />
                <div className="text-xs text-muted-foreground/60">
                  {t("library.skillsImport.hints.command")}
                </div>
              </TabsContent>
            </Tabs>
          )}

          {hasPreview && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <div className="text-sm text-muted-foreground">
                  {t("library.skillsImport.preview.found")}{" "}
                  <span className="text-foreground font-medium">
                    {candidates.length}
                  </span>{" "}
                  {t("library.skillsImport.preview.items")}
                  {overwriteCount > 0 && (
                    <span className="ml-2">
                      · {t("library.skillsImport.preview.overwrite")}{" "}
                      <span className="text-foreground font-medium">
                        {overwriteCount}
                      </span>{" "}
                      {t("library.skillsImport.preview.overwriteItems")}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="icon"
                    disabled={selectionDisabled || pagedCandidates.length === 0}
                    onClick={() => {
                      const targetSelected = !isPageFullySelected;
                      setSelections((prev) => {
                        const next = { ...prev };
                        for (const c of pagedCandidates) {
                          const current = next[c.relative_path] || {
                            selected: false,
                            nameOverride: "",
                          };
                          next[c.relative_path] = {
                            ...current,
                            selected: targetSelected,
                          };
                        }
                        return next;
                      });
                    }}
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
                    onClick={() => {
                      const targetSelected = !isAllSelected;
                      setSelections((prev) => {
                        const next = { ...prev };
                        for (const c of candidates) {
                          const current = next[c.relative_path] || {
                            selected: false,
                            nameOverride: "",
                          };
                          next[c.relative_path] = {
                            ...current,
                            selected: targetSelected,
                          };
                        }
                        return next;
                      });
                    }}
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
                  const sel = selections[c.relative_path] || {
                    selected: false,
                    nameOverride: "",
                  };
                  const disabled = selectionDisabled;
                  return (
                    <div
                      key={c.relative_path}
                      role="button"
                      tabIndex={0}
                      className="flex items-start gap-3 rounded-xl border border-border/50 bg-muted/10 px-4 py-3 cursor-pointer transition-colors hover:bg-muted/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:ring-offset-2"
                      onClick={(e) => {
                        if (disabled) return;
                        if ((e.target as HTMLElement).closest("input")) return;
                        setSelections((prev) => ({
                          ...prev,
                          [c.relative_path]: {
                            ...sel,
                            selected: !sel.selected,
                          },
                        }));
                      }}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          if (!disabled)
                            setSelections((prev) => ({
                              ...prev,
                              [c.relative_path]: {
                                ...sel,
                                selected: !sel.selected,
                              },
                            }));
                        }
                      }}
                    >
                      <span onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          className="self-center"
                          checked={sel.selected}
                          disabled={disabled}
                          onCheckedChange={(checked) => {
                            setSelections((prev) => ({
                              ...prev,
                              [c.relative_path]: {
                                ...sel,
                                selected: Boolean(checked),
                              },
                            }));
                          }}
                        />
                      </span>
                      <div className="flex-1 min-w-0 space-y-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium truncate">
                            {c.skill_name ||
                              t("library.skillsImport.preview.unnamed")}
                          </span>
                          {c.will_overwrite && (
                            <Badge variant="outline" className="text-xs">
                              {t("library.skillsImport.preview.willOverwrite")}
                            </Badge>
                          )}
                          {c.relative_path === "." && (
                            <Badge variant="outline" className="text-xs">
                              {t("library.skillsImport.preview.root")}
                            </Badge>
                          )}
                        </div>

                        {c.requires_name && sel.selected && (
                          <div
                            className="space-y-1"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                              {t("library.skillsImport.fields.nameOverride")}
                            </Label>
                            <Input
                              value={sel.nameOverride}
                              disabled={disabled}
                              onChange={(e) => {
                                const v = e.target.value;
                                setSelections((prev) => ({
                                  ...prev,
                                  [c.relative_path]: {
                                    ...sel,
                                    nameOverride: v,
                                  },
                                }));
                              }}
                              placeholder={t(
                                "library.skillsImport.placeholders.name",
                              )}
                              className="font-mono"
                            />
                            <div className="text-xs text-muted-foreground">
                              {t("library.skillsImport.hints.nameRequired")}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>

              {totalCandidatePages > 1 && (
                <div className="flex items-center justify-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={
                      isCommitting || isDiscovering || candidatePageClamped <= 1
                    }
                    onClick={() =>
                      setCandidatePage((prev) => Math.max(1, prev - 1))
                    }
                  >
                    {t("library.skillsImport.preview.pagination.prev")}
                  </Button>
                  <div className="text-xs text-muted-foreground">
                    {t("library.skillsImport.preview.pagination.page", {
                      page: candidatePageClamped,
                      pages: totalCandidatePages,
                    })}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={
                      isCommitting ||
                      isDiscovering ||
                      candidatePageClamped >= totalCandidatePages
                    }
                    onClick={() =>
                      setCandidatePage((prev) =>
                        Math.min(totalCandidatePages, prev + 1),
                      )
                    }
                  >
                    {t("library.skillsImport.preview.pagination.next")}
                  </Button>
                </div>
              )}

              {commitResult && (
                <div className="rounded-xl border border-border/50 bg-muted/5 px-4 py-3 space-y-2">
                  <div className="text-sm font-medium">
                    {t("library.skillsImport.result.title")}
                  </div>
                  <div className="space-y-1">
                    {(commitResult.items || []).map((it) => (
                      <div
                        key={it.relative_path}
                        className="text-xs text-muted-foreground flex items-center justify-between gap-2"
                      >
                        <span className="font-mono truncate">
                          {it.skill_name || it.relative_path}
                        </span>
                        <span className="shrink-0">
                          {it.status === "success"
                            ? t("library.skillsImport.result.success")
                            : t("library.skillsImport.result.failed")}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {commitError && !isCommitting && (
                <div className="rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 space-y-1">
                  <div className="text-sm font-medium">
                    {t("library.skillsImport.result.failed")}
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
