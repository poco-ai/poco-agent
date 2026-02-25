"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { useT } from "@/lib/i18n/client";
import { subAgentsService } from "@/features/capabilities/sub-agents/api/sub-agents-api";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentUpdateInput,
} from "@/features/capabilities/sub-agents/types";

export function useSubAgentsStore() {
  const { t } = useT("translation");
  const [subAgents, setSubAgents] = useState<SubAgent[]>([]);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await subAgentsService.list({ revalidate: 0 });
      setSubAgents(data);
    } catch (error) {
      console.error("[SubAgents] Failed to fetch:", error);
      toast.error(t("library.subAgents.toasts.loadError"));
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const createSubAgent = useCallback(
    async (input: SubAgentCreateInput) => {
      setSavingId(-1);
      try {
        const created = await subAgentsService.create(input);
        setSubAgents((prev) => [created, ...prev]);
        toast.success(t("library.subAgents.toasts.created"));
        return created;
      } catch (error) {
        console.error("[SubAgents] create failed:", error);
        toast.error(t("library.subAgents.toasts.error"));
        return null;
      } finally {
        setSavingId(null);
      }
    },
    [t],
  );

  const updateSubAgent = useCallback(
    async (subAgentId: number, input: SubAgentUpdateInput) => {
      setSavingId(subAgentId);
      try {
        const updated = await subAgentsService.update(subAgentId, input);
        setSubAgents((prev) =>
          prev.map((a) => (a.id === subAgentId ? updated : a)),
        );
        toast.success(t("library.subAgents.toasts.updated"));
        return updated;
      } catch (error) {
        console.error("[SubAgents] update failed:", error);
        toast.error(t("library.subAgents.toasts.error"));
        return null;
      } finally {
        setSavingId(null);
      }
    },
    [t],
  );

  const deleteSubAgent = useCallback(
    async (subAgentId: number) => {
      setSavingId(subAgentId);
      try {
        await subAgentsService.remove(subAgentId);
        setSubAgents((prev) => prev.filter((a) => a.id !== subAgentId));
        toast.success(t("library.subAgents.toasts.deleted"));
      } catch (error) {
        console.error("[SubAgents] delete failed:", error);
        toast.error(t("library.subAgents.toasts.error"));
      } finally {
        setSavingId(null);
      }
    },
    [t],
  );

  const setEnabled = useCallback(
    async (subAgentId: number, enabled: boolean) => {
      // Optimistic update
      setSubAgents((prev) =>
        prev.map((a) => (a.id === subAgentId ? { ...a, enabled } : a)),
      );
      const updated = await updateSubAgent(subAgentId, { enabled });
      if (!updated) {
        // Rollback
        setSubAgents((prev) =>
          prev.map((a) =>
            a.id === subAgentId ? { ...a, enabled: !enabled } : a,
          ),
        );
      }
    },
    [updateSubAgent],
  );

  return {
    subAgents,
    isLoading,
    savingId,
    refresh,
    createSubAgent,
    updateSubAgent,
    deleteSubAgent,
    setEnabled,
  };
}
