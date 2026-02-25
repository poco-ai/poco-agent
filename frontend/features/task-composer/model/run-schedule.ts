export type RunScheduleMode = "immediate" | "scheduled" | "nightly";

export interface RunScheduleValue {
  schedule_mode: RunScheduleMode;
  timezone: string;
  scheduled_at: string | null;
}
