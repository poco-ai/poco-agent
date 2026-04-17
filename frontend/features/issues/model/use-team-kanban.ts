"use client";

import * as React from "react";
import { useRouter, useSearchParams } from "next/navigation";

export function useTeamKanban(lng?: string) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const locale = lng ?? "en";
  const queryIssueId = searchParams.get("issue");
  const [selectedIssueId, setSelectedIssueId] = React.useState<string | null>(
    queryIssueId,
  );

  React.useEffect(() => {
    setSelectedIssueId(queryIssueId);
  }, [queryIssueId]);

  const openIssue = React.useCallback(
    (issueId: string) => {
      setSelectedIssueId(issueId);
      const params = new URLSearchParams(searchParams.toString());
      params.set("issue", issueId);
      router.replace(`/${locale}/team/issues?${params.toString()}`, {
        scroll: false,
      });
    },
    [locale, router, searchParams],
  );

  const closeIssue = React.useCallback(() => {
    setSelectedIssueId(null);
    const params = new URLSearchParams(searchParams.toString());
    params.delete("issue");
    const query = params.toString();
    router.replace(`/${locale}/team/issues${query ? `?${query}` : ""}`, {
      scroll: false,
    });
  }, [locale, router, searchParams]);

  return {
    selectedIssueId,
    openIssue,
    closeIssue,
  };
}
