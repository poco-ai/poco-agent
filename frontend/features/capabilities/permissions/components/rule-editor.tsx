"use client";

import * as React from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useT } from "@/lib/i18n/client";
import type { PermissionRule } from "../types";
import { TOOL_CATEGORIES } from "../types";

const genId = () => Math.random().toString(36).slice(2, 10);

interface RuleEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initial?: PermissionRule | null;
  onSave: (rule: PermissionRule) => void;
}

const EMPTY_RULE: PermissionRule = {
  id: "",
  priority: 100,
  match: {},
  action: "allow",
  reason: "",
  enabled: true,
};

function tagsToArray(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function arrayToTags(arr: string[] | null | undefined): string {
  return (arr ?? []).join(", ");
}

export function RuleEditor({
  open,
  onOpenChange,
  initial,
  onSave,
}: RuleEditorProps) {
  const { t } = useT("translation");
  const [rule, setRule] = React.useState<PermissionRule>(EMPTY_RULE);

  React.useEffect(() => {
    if (open) {
      setRule(initial ? { ...initial } : { ...EMPTY_RULE, id: genId() });
    }
  }, [open, initial]);

  const handleSave = () => {
    onSave(rule);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {initial
              ? t("permissions.rule.editTitle", "Edit Rule")
              : t("permissions.rule.addTitle", "Add Rule")}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <Label>{t("permissions.rule.action", "Action")}</Label>
              <Select
                value={rule.action}
                onValueChange={(v) =>
                  setRule((r) => ({
                    ...r,
                    action: v as PermissionRule["action"],
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="allow">{t("permissions.rule.allow", "Allow")}</SelectItem>
                  <SelectItem value="deny">{t("permissions.rule.deny", "Deny")}</SelectItem>
                  <SelectItem value="ask">{t("permissions.rule.ask", "Ask")}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <Label>{t("permissions.rule.priority", "Priority")}</Label>
              <Input
                type="number"
                min={1}
                max={999}
                value={rule.priority}
                onChange={(e) =>
                  setRule((r) => ({
                    ...r,
                    priority: Number(e.target.value) || 100,
                  }))
                }
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label>{t("permissions.rule.tools", "Tools (comma-separated)")}</Label>
            <Input
              placeholder="Bash, Write, Edit"
              value={arrayToTags(rule.match.tools)}
              onChange={(e) =>
                setRule((r) => ({
                  ...r,
                  match: { ...r.match, tools: tagsToArray(e.target.value) || null },
                }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label>{t("permissions.rule.categories", "Tool Categories")}</Label>
            <Select
              value={rule.match.tool_categories?.[0] ?? ""}
              onValueChange={(v) =>
                setRule((r) => ({
                  ...r,
                  match: {
                    ...r.match,
                    tool_categories: v ? [v] : null,
                  },
                }))
              }
            >
              <SelectTrigger>
                <SelectValue placeholder={t("permissions.rule.anyCategory", "Any category")} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">{t("permissions.rule.anyCategory", "Any category")}</SelectItem>
                {TOOL_CATEGORIES.map((cat) => (
                  <SelectItem key={cat} value={cat}>
                    {cat}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>{t("permissions.rule.pathPatterns", "Path Patterns (comma-separated)")}</Label>
            <Input
              placeholder="/tmp/**, /home/**"
              value={arrayToTags(rule.match.path_patterns)}
              onChange={(e) =>
                setRule((r) => ({
                  ...r,
                  match: { ...r.match, path_patterns: tagsToArray(e.target.value) || null },
                }))
              }
            />
          </div>

          <div className="space-y-1.5">
            <Label>{t("permissions.rule.reason", "Reason / Description")}</Label>
            <Input
              placeholder={t("permissions.rule.reasonPlaceholder", "Why this rule exists")}
              value={rule.reason}
              onChange={(e) => setRule((r) => ({ ...r, reason: e.target.value }))}
            />
          </div>

          <div className="flex items-center justify-between">
            <Label>{t("permissions.rule.enabled", "Enabled")}</Label>
            <Switch
              checked={rule.enabled}
              onCheckedChange={(checked) =>
                setRule((r) => ({ ...r, enabled: checked }))
              }
            />
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t("common.cancel", "Cancel")}
          </Button>
          <Button onClick={handleSave}>
            {t("common.save", "Save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
