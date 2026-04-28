import type { LucideIcon } from "lucide-react";

export type SettingsTabId = "account" | "usage" | "shortcuts" | "admin";

export type SettingsTabRequest = {
  tab: SettingsTabId;
  requestId: number;
};

export interface SettingsSidebarItem {
  id: SettingsTabId;
  label: string;
  icon: LucideIcon;
}

export interface UsageAnalyticsMetricSummary {
  input_tokens: number;
  output_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  total_tokens: number;
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

export interface ModelDefinitionResponse {
  model_id: string;
  display_name: string;
  provider_id: string;
  requires_credentials: boolean;
  supports_custom_base_url: boolean;
}

export interface ModelProviderResponse {
  provider_id: string;
  display_name: string;
  api_key_env_key: string;
  base_url_env_key: string;
  credential_state: "none" | "system" | "user";
  default_base_url: string;
  effective_base_url: string;
  base_url_source: "default" | "system" | "user";
  known_models: [string, string][];
  models: ModelDefinitionResponse[];
}

export interface ModelConfigResponse {
  default_model: string;
  model_list: string[];
  mem0_enabled: boolean;
  models: ModelDefinitionResponse[];
  providers: ModelProviderResponse[];
}
