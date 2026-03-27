import * as React from "react";

import {
  getDeliverablesAction,
  getDeliverableVersionAction,
  getDeliverableVersionsAction,
} from "@/features/chat/actions/query-actions";
import type {
  DeliverableResponse,
  DeliverableVersionResponse,
} from "@/features/chat/types";

interface UseSessionDeliverablesOptions {
  sessionId?: string;
  isActive?: boolean;
  pollingIntervalMs?: number;
}

interface UseSessionDeliverablesReturn {
  deliverables: DeliverableResponse[];
  versionMap: Record<string, DeliverableVersionResponse>;
  versionsByDeliverableId: Record<string, DeliverableVersionResponse[]>;
  isLoading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  ensureVersion: (
    versionId: string | null | undefined,
  ) => Promise<DeliverableVersionResponse | null>;
  ensureVersionsForDeliverable: (
    deliverableId: string | null | undefined,
  ) => Promise<DeliverableVersionResponse[]>;
}

export function useSessionDeliverables({
  sessionId,
  isActive = false,
  pollingIntervalMs = 4000,
}: UseSessionDeliverablesOptions): UseSessionDeliverablesReturn {
  const [deliverables, setDeliverables] = React.useState<DeliverableResponse[]>(
    [],
  );
  const [versionMap, setVersionMap] = React.useState<
    Record<string, DeliverableVersionResponse>
  >({});
  const [versionsByDeliverableId, setVersionsByDeliverableId] = React.useState<
    Record<string, DeliverableVersionResponse[]>
  >({});
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

  const refresh = React.useCallback(async () => {
    if (!sessionId) {
      setDeliverables([]);
      setVersionMap({});
      setVersionsByDeliverableId({});
      setIsLoading(false);
      setError(null);
      return;
    }

    try {
      const items = await getDeliverablesAction({ sessionId });
      setDeliverables(items);
      setError(null);
    } catch (nextError) {
      setError(nextError as Error);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  React.useEffect(() => {
    setIsLoading(true);
    void refresh();
  }, [refresh]);

  React.useEffect(() => {
    if (!sessionId || !isActive) return undefined;
    const timer = window.setInterval(() => {
      void refresh();
    }, pollingIntervalMs);
    return () => window.clearInterval(timer);
  }, [isActive, pollingIntervalMs, refresh, sessionId]);

  const ensureVersion = React.useCallback(
    async (
      versionId: string | null | undefined,
    ): Promise<DeliverableVersionResponse | null> => {
      if (!sessionId || !versionId) return null;
      const cached = versionMap[versionId];
      if (cached) return cached;

      const version = await getDeliverableVersionAction({
        sessionId,
        versionId,
      });
      setVersionMap((current) => ({
        ...current,
        [versionId]: version,
      }));
      return version;
    },
    [sessionId, versionMap],
  );

  const ensureVersionsForDeliverable = React.useCallback(
    async (deliverableId: string | null | undefined) => {
      if (!sessionId || !deliverableId) return [];
      const cached = versionsByDeliverableId[deliverableId];
      if (cached) return cached;

      const versions = await getDeliverableVersionsAction({
        sessionId,
        deliverableId,
      });
      setVersionsByDeliverableId((current) => ({
        ...current,
        [deliverableId]: versions,
      }));
      setVersionMap((current) => {
        const next = { ...current };
        for (const version of versions) {
          next[version.id] = version;
        }
        return next;
      });
      return versions;
    },
    [sessionId, versionsByDeliverableId],
  );

  return {
    deliverables,
    versionMap,
    versionsByDeliverableId,
    isLoading,
    error,
    refresh,
    ensureVersion,
    ensureVersionsForDeliverable,
  };
}
