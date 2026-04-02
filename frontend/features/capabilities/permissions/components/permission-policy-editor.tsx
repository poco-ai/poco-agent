"use client";

import * as React from "react";
import { Plus, Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useT } from "@/lib/i18n/client";
import type { PermissionPolicy, PermissionRule } from "../types";
import { PRESET_SOURCES } from "../types";
import { PolicyModeToggle } from "./policy-mode-toggle";
import { RuleList } from "./rule-list";
import { RuleEditor } from "./rule-editor";

interface PermissionPolicyEditorProps {
  policy: PermissionPolicy;
  isSaving: boolean;
  onChange: (policy: PermissionPolicy) => void;
  onSave: (policy: PermissionPolicy) => void;
}

export function PermissionPolicyEditor({
  policy,
  isSaving,
  onChange,
  onSave,
}: PermissionPolicyEditorProps) {
  const { t } = useT("translation");
  const [editorOpen, setEditorOpen] = React.useState(false);
  const [editingRule, setEditingRule] = React.useState<PermissionRule | null>(null);

  const handleAddRule = (rule: PermissionRule) => {
    onChange({ ...policy, rules: [...policy.rules, rule] });
  };

  const handleUpdateRule = (rule: PermissionRule) => {
    onChange({
      ...policy,
      rules: policy.rules.map((r) => (r.id === rule.id ? rule : r)),
    });
  };

  const handleDeleteRule = (id: string) => {
    onChange({ ...policy, rules: policy.rules.filter((r) => r.id !== id) });
  };

  const handleToggleRule = (id: string, enabled: boolean) => {
    onChange({
      ...policy,
      rules: policy.rules.map((r) => (r.id === id ? { ...r, enabled } : r)),
    });
  };

  const openEdit = (rule: PermissionRule) => {
    setEditingRule(rule);
    setEditorOpen(true);
  };

  const openAdd = () => {
    setEditingRule(null);
    setEditorOpen(true);
  };

  return (
    <div className="space-y-5">
      <PolicyModeToggle
        mode={policy.mode}
        onChange={(mode) => onChange({ ...policy, mode })}
      />

      <div className="space-y-3 rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-md">
        <div className="space-y-1">
          <Label>{t("permissions.preset.label", "Preset Source")}</Label>
          <p className="text-xs text-muted-foreground">
            {t("permissions.preset.hint", "Base permission mode inherited from Claude Code presets")}
          </p>
        </div>
        <Select
          value={policy.preset_source ?? "default"}
          onValueChange={(v) =>
            onChange({ ...policy, preset_source: v === "default" ? null : v })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PRESET_SOURCES.map((src) => (
              <SelectItem key={src} value={src}>
                {src}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-3 rounded-2xl border border-border/60 bg-card/60 p-4 backdrop-blur-md">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <Label>{t("permissions.rules.title", "Custom Rules")}</Label>
            <p className="text-xs text-muted-foreground">
              {t("permissions.rules.hint", "Rules are evaluated by priority (lower number = higher priority)")}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={openAdd}>
            <Plus className="mr-1.5 size-3.5" />
            {t("permissions.rules.add", "Add Rule")}
          </Button>
        </div>

        <RuleList
          rules={policy.rules}
          onEdit={openEdit}
          onDelete={handleDeleteRule}
          onToggle={handleToggleRule}
        />
      </div>

      <div className="flex justify-end">
        <Button onClick={() => onSave(policy)} disabled={isSaving}>
          {isSaving ? (
            <Loader2 className="mr-2 size-4 animate-spin" />
          ) : (
            <Save className="mr-2 size-4" />
          )}
          {t("permissions.save", "Save Policy")}
        </Button>
      </div>

      <RuleEditor
        open={editorOpen}
        onOpenChange={setEditorOpen}
        initial={editingRule}
        onSave={(rule) => {
          if (editingRule) {
            handleUpdateRule(rule);
          } else {
            handleAddRule(rule);
          }
        }}
      />
    </div>
  );
}
