import type { LucideIcon } from "lucide-react";
import type {
  BaseUrlSource,
  CredentialState,
  ModelProvider,
} from "@/features/chat/types/api/models";

export type SettingsTabId = "account" | "models" | "usage" | "shortcuts";

export type SettingsTabRequest = {
  tab: SettingsTabId;
  requestId: number;
};

export interface SettingsSidebarItem {
  id: SettingsTabId;
  label: string;
  icon: LucideIcon;
}

export type ApiProviderConfig = {
  providerId: string;
  displayName: string;
  apiKeyEnvKey: string;
  baseUrlEnvKey: string;
  credentialState: CredentialState;
  defaultBaseUrl: string;
  effectiveBaseUrl: string;
  baseUrlSource: BaseUrlSource;
  models: ModelProvider["models"];
  selectedModelIds: string[];
  modelDraft: string;
  keyInput: string;
  baseUrlInput: string;
  hasStoredUserKey: boolean;
  hasStoredUserBaseUrl: boolean;
  isSaving: boolean;
};
export interface UsageAnalyticsMetricSummary {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
}

export interface UsageAnalyticsBucket extends UsageAnalyticsMetricSummary {
  bucket_id: string;
  label: string;
}

export interface UsageAnalyticsSummary {
  month: UsageAnalyticsMetricSummary;
  day: UsageAnalyticsMetricSummary;
  all_time: UsageAnalyticsMetricSummary;
}

export interface UsageAnalyticsMonthView {
  month: string;
  buckets: UsageAnalyticsBucket[];
}

export interface UsageAnalyticsDayView {
  day: string;
  buckets: UsageAnalyticsBucket[];
}

export interface UsageAnalyticsResponse {
  timezone: string;
  month: string;
  day: string;
  summary: UsageAnalyticsSummary;
  month_view: UsageAnalyticsMonthView;
  day_view: UsageAnalyticsDayView;
}
