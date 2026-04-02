"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Pencil, Trash2, GripVertical } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";
import type { PermissionRule } from "../types";

interface RuleListProps {
  rules: PermissionRule[];
  onEdit: (rule: PermissionRule) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string, enabled: boolean) => void;
}

const ACTION_COLORS: Record<string, string> = {
  allow: "bg-green-500/10 text-green-600 border-green-500/20",
  deny: "bg-red-500/10 text-red-600 border-red-500/20",
  ask: "bg-yellow-500/10 text-yellow-600 border-yellow-500/20",
};

function matchSummary(rule: PermissionRule): string {
  const parts: string[] = [];
  if (rule.match.tools?.length) parts.push(`tools: ${rule.match.tools.join(", ")}`);
  if (rule.match.tool_categories?.length) parts.push(`cat: ${rule.match.tool_categories.join(", ")}`);
  if (rule.match.path_patterns?.length) parts.push(`paths: ${rule.match.path_patterns.join(", ")}`);
  if (rule.match.network_patterns?.length) parts.push(`net: ${rule.match.network_patterns.join(", ")}`);
  if (rule.match.mcp_servers?.length) parts.push(`mcp: ${rule.match.mcp_servers.join(", ")}`);
  return parts.length ? parts.join(" · ") : "*";
}

export function RuleList({ rules, onEdit, onDelete, onToggle }: RuleListProps) {
  const { t } = useT("translation");

  if (rules.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border/60 py-8 text-center text-sm text-muted-foreground">
        {t("permissions.rules.empty", "No custom rules — using preset defaults")}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {rules.map((rule) => (
        <div
          key={rule.id}
          className={cn(
            "flex items-center gap-3 rounded-xl border border-border/60 bg-background/60 px-3 py-2.5",
            !rule.enabled && "opacity-50",
          )}
        >
          <GripVertical className="size-4 shrink-0 text-muted-foreground/40" />

          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={cn("text-xs font-mono", ACTION_COLORS[rule.action])}
              >
                {rule.action}
              </Badge>
              <span className="truncate font-mono text-xs text-muted-foreground">
                {matchSummary(rule)}
              </span>
            </div>
            {rule.reason && (
              <span className="truncate text-xs text-muted-foreground/70">
                {rule.reason}
              </span>
            )}
          </div>

          <span className="shrink-0 text-xs text-muted-foreground/50">
            p{rule.priority}
          </span>

          <Switch
            checked={rule.enabled}
            onCheckedChange={(checked) => onToggle(rule.id, checked)}
            className="shrink-0"
          />

          <Button
            variant="ghost"
            size="icon"
            className="size-7 shrink-0"
            onClick={() => onEdit(rule)}
          >
            <Pencil className="size-3.5" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            className="size-7 shrink-0 text-destructive hover:text-destructive"
            onClick={() => onDelete(rule.id)}
          >
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      ))}
    </div>
  );
}
