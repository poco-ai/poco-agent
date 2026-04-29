"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

export function useTeamKanban(lng?: string) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = lng ?? "en";
  const queryIssueId = searchParams.get("issue");

  const openIssue = React.useCallback(
    (issueId: string) => {
      if (queryIssueId === issueId) {
        return;
      }
      const params = new URLSearchParams(searchParams.toString());
      params.set("issue", issueId);
      router.replace(`/${locale}/team/issues?${params.toString()}`, {
        scroll: false,
      });
    },
    [locale, queryIssueId, router, searchParams],
  );

  const closeIssue = React.useCallback(() => {
    if (!queryIssueId) {
      return;
    }
    const params = new URLSearchParams(searchParams.toString());
    params.delete("issue");
    const query = params.toString();
    router.replace(`/${locale}/team/issues${query ? `?${query}` : ""}`, {
      scroll: false,
    });
  }, [locale, queryIssueId, router, searchParams]);

  return {
    selectedIssueId: queryIssueId,
    openIssue,
    closeIssue,
  };
}
