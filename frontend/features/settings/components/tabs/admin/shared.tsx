import * as React from "react";

import { AlertCircle, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useT } from "@/lib/i18n/client";

export function parseJsonObject(
  value: string,
  errorMessage: string,
): Record<string, unknown> {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error(errorMessage);
  }
  if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
    throw new Error(errorMessage);
  }
  return parsed as Record<string, unknown>;
}

export function summarizeJson(value: unknown): string {
  const text = JSON.stringify(value);
  if (!text) return "-";
  return text.length > 140 ? `${text.slice(0, 140)}...` : text;
}

export function AdminPolicyHint() {
  const { t } = useT("translation");

  return (
    <div className="rounded-lg border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
      {t("settings.admin.policyDescription")}
    </div>
  );
}

interface AdminLabeledInputFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export function AdminLabeledInputField({
  label,
  value,
  onChange,
  placeholder,
}: AdminLabeledInputFieldProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

interface AdminLabeledTextareaFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function AdminLabeledTextareaField({
  label,
  value,
  onChange,
  placeholder,
  className,
}: AdminLabeledTextareaFieldProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <Textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={className}
      />
    </div>
  );
}

interface AdminPolicySwitchFieldProps {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function AdminPolicySwitchField({
  label,
  checked,
  onCheckedChange,
}: AdminPolicySwitchFieldProps) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
        <Switch checked={checked} onCheckedChange={onCheckedChange} />
      </div>
    </div>
  );
}

interface AdminPolicySwitchInlineProps {
  label: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}

export function AdminPolicySwitchInline({
  label,
  checked,
  onCheckedChange,
}: AdminPolicySwitchInlineProps) {
  return (
    <div className="flex items-center gap-3 rounded-md border border-border px-3 py-2">
      <Switch checked={checked} onCheckedChange={onCheckedChange} />
      <span className="text-sm text-muted-foreground">{label}</span>
    </div>
  );
}

export function AdminMaskedUpdateHint() {
  const { t } = useT("translation");

  return (
    <div className="text-xs text-muted-foreground">
      {t("settings.admin.maskedUpdateHint")}
    </div>
  );
}

export function AdminCreateActions({
  isSaving,
  onCreate,
}: {
  isSaving: boolean;
  onCreate: () => void;
}) {
  const { t } = useT("translation");

  return (
    <Button onClick={() => void onCreate()} disabled={isSaving}>
      {t("settings.admin.create")}
    </Button>
  );
}

export function AdminCreateGrid({
  children,
  columns = "two",
}: {
  children: React.ReactNode;
  columns?: "two" | "three";
}) {
  return (
    <div
      className={
        columns === "three"
          ? "grid gap-3 md:grid-cols-3"
          : "grid gap-3 md:grid-cols-2"
      }
    >
      {children}
    </div>
  );
}

export function AdminSectionLoading() {
  const { t } = useT("translation");

  return (
    <div className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
      {t("settings.admin.loading")}
    </div>
  );
}

export function AdminSectionError({ onRetry }: { onRetry: () => void }) {
  const { t } = useT("translation");

  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-destructive/40 bg-destructive/5 px-3 py-6 text-center">
      <div className="flex items-center gap-2 text-sm text-destructive">
        <AlertCircle className="size-4" />
        <span>{t("settings.admin.loadFailed")}</span>
      </div>
      <Button variant="outline" size="sm" onClick={onRetry}>
        {t("settings.admin.refresh")}
      </Button>
    </div>
  );
}

interface AdminItemActionsProps {
  isSaving: boolean;
  onEdit: () => void;
  onDelete: () => void;
}

export function AdminItemActions({
  isSaving,
  onEdit,
  onDelete,
}: AdminItemActionsProps) {
  const { t } = useT("translation");

  return (
    <>
      <Button variant="outline" size="sm" onClick={onEdit} disabled={isSaving}>
        {t("settings.admin.edit")}
      </Button>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => void onDelete()}
        disabled={isSaving}
      >
        <Trash2 className="size-4" />
      </Button>
    </>
  );
}

interface AdminEditActionsProps {
  isSaving: boolean;
  onCancel: () => void;
  onSave: () => void;
}

export function AdminEditActions({
  isSaving,
  onCancel,
  onSave,
}: AdminEditActionsProps) {
  const { t } = useT("translation");

  return (
    <div className="flex justify-end gap-2">
      <Button variant="outline" onClick={onCancel} disabled={isSaving}>
        {t("settings.admin.cancel")}
      </Button>
      <Button onClick={() => void onSave()} disabled={isSaving}>
        {t("settings.admin.update")}
      </Button>
    </div>
  );
}

export function SectionCard({
  title,
  description,
  actions,
  children,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-4 rounded-xl border border-border bg-card p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="text-sm font-medium">{title}</div>
          {description ? (
            <div className="text-xs text-muted-foreground">{description}</div>
          ) : null}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function ListItem({
  title,
  description,
  badge,
  danger,
  children,
}: {
  title: string;
  description?: string;
  badge?: React.ReactNode;
  danger?: React.ReactNode;
  children?: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border px-3 py-3">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="truncate font-medium">{title}</div>
            {badge}
          </div>
          {description ? (
            <div className="break-all text-xs text-muted-foreground">
              {description}
            </div>
          ) : null}
        </div>
        <div className="flex shrink-0 items-center gap-2">{danger}</div>
      </div>
      {children ? (
        <div className="mt-3 border-t border-border pt-3">{children}</div>
      ) : null}
    </div>
  );
}
