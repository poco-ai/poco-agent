"use client";

import * as React from "react";

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
import { Label } from "@/components/ui/label";
import type { FileNode } from "@/features/chat/types";
import { useT } from "@/lib/i18n/client";

interface PackageSkillDialogProps {
  open: boolean;
  folder: FileNode | null;
  submitting?: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: (payload: { folder_path: string; skill_name?: string }) => Promise<void>;
}

function defaultSkillName(folder: FileNode | null): string {
  if (!folder) return "";
  return folder.path.split("/").filter(Boolean).pop() || folder.name || "";
}

export function PackageSkillDialog({
  open,
  folder,
  submitting = false,
  onOpenChange,
  onConfirm,
}: PackageSkillDialogProps) {
  const { t } = useT("translation");
  const [skillName, setSkillName] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setSkillName(defaultSkillName(folder));
  }, [folder, open]);

  const handleConfirm = async () => {
    if (!folder) return;
    const normalized = skillName.trim();
    await onConfirm({
      folder_path: folder.path,
      skill_name: normalized || undefined,
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("fileSidebar.packageSkillTitle")}</DialogTitle>
          <DialogDescription>
            {t("fileSidebar.packageSkillDescription")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="package-skill-name">
              {t("fileSidebar.skillName")}
            </Label>
            <Input
              id="package-skill-name"
              value={skillName}
              onChange={(event) => setSkillName(event.target.value)}
              placeholder={t("fileSidebar.skillNamePlaceholder")}
              autoFocus
            />
          </div>
          <div className="rounded-md border border-border/60 bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
            {folder?.path}
          </div>
        </div>
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            {t("common.cancel")}
          </Button>
          <Button type="button" onClick={handleConfirm} disabled={submitting}>
            {submitting ? t("common.saving") : t("fileSidebar.submitSkill")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
