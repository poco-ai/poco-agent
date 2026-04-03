"use client";

import * as React from "react";

import { getRunsBySessionAction } from "@/features/chat/actions/query-actions";
import { cn } from "@/lib/utils";
import { McpStateMachineCard } from "./mcp-state-machine-card";

interface McpHistorySectionProps {
  sessionId?: string | null;
  sessionTime?: string | null;
  show: boolean;
  className?: string;
}

function pickLatestRunId(runs: Array<{ run_id: string }> | null | undefined) {
  if (!Array.isArray(runs) || runs.length === 0) {
    return null;
  }
  const latestRun = runs.at(-1);
  return latestRun?.run_id ?? null;
}

export function McpHistorySection({
  sessionId,
  sessionTime,
  show,
  className,
}: McpHistorySectionProps) {
  const [runId, setRunId] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!show || !sessionId) {
      setRunId(null);
      return;
    }

    let cancelled = false;

    const loadLatestRun = async () => {
      try {
        const runs = await getRunsBySessionAction({ sessionId });
        if (!cancelled) {
          setRunId(pickLatestRunId(runs));
        }
      } catch {
        if (!cancelled) {
          setRunId(null);
        }
      }
    };

    void loadLatestRun();

    return () => {
      cancelled = true;
    };
  }, [sessionId, sessionTime, show]);

  if (!show || !runId) {
    return null;
  }

  return (
    <div className={cn("pb-2 shrink-0", className)}>
      <McpStateMachineCard runId={runId} />
    </div>
  );
}
