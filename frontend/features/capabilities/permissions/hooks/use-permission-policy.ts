"use client";

import * as React from "react";
import { toast } from "sonner";
import { useT } from "@/lib/i18n/client";
import {
  getPermissionPolicy,
  updatePermissionPolicy,
} from "../api/permissions-api";
import type { PermissionPolicy, PermissionRule } from "../types";
import { DEFAULT_POLICY } from "../types";

export function usePermissionPolicy() {
  const { t } = useT("translation");
  const [policy, setPolicy] = React.useState<PermissionPolicy>(DEFAULT_POLICY);
  const [isLoading, setIsLoading] = React.useState(true);
  const [isSaving, setIsSaving] = React.useState(false);

  React.useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        setIsLoading(true);
        const p = await getPermissionPolicy();
        if (!cancelled) setPolicy(p);
      } catch {
        // silent
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const save = React.useCallback(
    async (next: PermissionPolicy) => {
      try {
        setIsSaving(true);
        const saved = await updatePermissionPolicy(next);
        setPolicy(saved);
        toast.success(t("permissions.toasts.saved", "Permission policy saved"));
      } catch {
        toast.error(t("permissions.toasts.saveFailed", "Failed to save policy"));
      } finally {
        setIsSaving(false);
      }
    },
    [t],
  );

  const addRule = React.useCallback((rule: PermissionRule) => {
    setPolicy((p) => ({ ...p, rules: [...p.rules, rule] }));
  }, []);

  const updateRule = React.useCallback(
    (id: string, updates: Partial<PermissionRule>) => {
      setPolicy((p) => ({
        ...p,
        rules: p.rules.map((r) => (r.id === id ? { ...r, ...updates } : r)),
      }));
    },
    [],
  );

  const removeRule = React.useCallback((id: string) => {
    setPolicy((p) => ({ ...p, rules: p.rules.filter((r) => r.id !== id) }));
  }, []);

  const reorderRules = React.useCallback((rules: PermissionRule[]) => {
    setPolicy((p) => ({ ...p, rules }));
  }, []);

  return {
    policy,
    setPolicy,
    isLoading,
    isSaving,
    save,
    addRule,
    updateRule,
    removeRule,
    reorderRules,
  };
}
