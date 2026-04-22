"use client";

import * as React from "react";
import type { RunResponse } from "@/features/chat/types";
import { getRunFileChangeCount } from "@/features/chat/components/layout/run-timeline-utils";

interface RunRecordSummary {
  fileChangeCount: number;
  replayStepCount: number;
  updatedAt: string;
}

export function useRunRecordSummary(runs: RunResponse[], enabled = true) {
  return React.useMemo<Record<string, RunRecordSummary>>(() => {
    if (!enabled || runs.length === 0) {
      return {};
    }

    return runs.reduce<Record<string, RunRecordSummary>>((acc, run) => {
      acc[run.run_id] = {
        fileChangeCount: getRunFileChangeCount(run),
        replayStepCount: run.replay_step_count ?? 0,
        updatedAt: run.updated_at,
      };
      return acc;
    }, {});
  }, [enabled, runs]);
}
