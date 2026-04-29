import type { WorkspaceIssue } from "../model/types.ts";

export type IssueDetailLoadState = "loading" | "error" | "loaded";

export interface IssueDetailFormData {
  status: WorkspaceIssue["status"];
  priority: WorkspaceIssue["priority"];
  relatedProjectId: string;
  selectedPresetId: string;
  triggerMode: "persistent_sandbox" | "scheduled_task";
  scheduleCron: string;
  prompt: string;
}

export function createIssueDetailFormData(
  issue: WorkspaceIssue,
): IssueDetailFormData {
  return {
    status: issue.status,
    priority: issue.priority,
    relatedProjectId: issue.related_project_id ?? "none",
    selectedPresetId: issue.assignee_preset_id
      ? String(issue.assignee_preset_id)
      : "none",
    triggerMode: issue.agent_assignment?.trigger_mode ?? "persistent_sandbox",
    scheduleCron: issue.agent_assignment?.schedule_cron ?? "0 * * * *",
    prompt: issue.agent_assignment?.prompt ?? issue.description ?? "",
  };
}

export function getIssueDetailPrioritySelectValue(
  priority: WorkspaceIssue["priority"],
): "high" | "medium" | "low" {
  if (priority === "urgent" || priority === "high") {
    return "high";
  }
  if (priority === "low") {
    return "low";
  }
  return "medium";
}

export function shouldScheduleIssueDetailAutoSave(
  loadState: IssueDetailLoadState,
  shouldSkipNextProgrammaticSync: boolean,
): boolean {
  return loadState === "loaded" && !shouldSkipNextProgrammaticSync;
}
