"use client";

import * as React from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { Textarea } from "@/components/ui/textarea";
import type {
  WorkspaceBoard,
  WorkspaceBoardInput,
} from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";

interface TeamBoardSettingsDialogProps {
  board: WorkspaceBoard | null;
  issueCount: number;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (input: WorkspaceBoardInput) => Promise<void>;
  onDelete: () => Promise<void>;
}

export function TeamBoardSettingsDialog({
  board,
  issueCount,
  open,
  onOpenChange,
  onSave,
  onDelete,
}: TeamBoardSettingsDialogProps) {
  const { t } = useT("translation");
  const [name, setName] = React.useState("");
  const [description, setDescription] = React.useState("");
  const [isSaving, setIsSaving] = React.useState(false);
  const [isDeleting, setIsDeleting] = React.useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = React.useState(false);

  React.useEffect(() => {
    if (!open) {
      setDeleteDialogOpen(false);
      setIsSaving(false);
      setIsDeleting(false);
      return;
    }

    setName(board?.name ?? "");
    setDescription(board?.description ?? "");
  }, [board, open]);

  const handleSave = async () => {
    if (!board || !name.trim()) {
      return;
    }

    setIsSaving(true);
    try {
      await onSave({
        name: name.trim(),
        description: description.trim() || null,
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!board) {
      return;
    }

    setIsDeleting(true);
    try {
      await onDelete();
    } finally {
      setIsDeleting(false);
      setDeleteDialogOpen(false);
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("issues.dialogs.boardSettingsTitle")}</DialogTitle>
            <DialogDescription>
              {t("issues.dialogs.boardSettingsDescription")}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t("issues.fields.boardName")}
              </p>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder={t("issues.boardNamePlaceholder")}
              />
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                {t("issues.fields.boardDescription")}
              </p>
              <Textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                rows={4}
                placeholder={t("issues.context.noBoardDescription")}
              />
            </div>

            <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4">
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground">
                  {t("issues.actions.deleteBoard")}
                </p>
                <p className="text-sm text-muted-foreground">
                  {t("issues.dialogs.deleteBoardDescription", { count: issueCount })}
                </p>
              </div>
              <Button
                type="button"
                variant="outline"
                className="mt-4 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
                onClick={() => setDeleteDialogOpen(true)}
                disabled={!board}
              >
                {t("issues.actions.deleteBoard")}
              </Button>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button
              type="button"
              onClick={() => void handleSave()}
              disabled={!board || isSaving || !name.trim()}
            >
              {isSaving ? t("common.saving") : t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t("issues.dialogs.deleteBoardTitle")}</AlertDialogTitle>
            <AlertDialogDescription>
              {t("issues.dialogs.deleteBoardDescription", { count: issueCount })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isDeleting}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDelete()}>
              {isDeleting
                ? t("issues.actions.deletingBoard")
                : t("issues.actions.deleteBoard")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
