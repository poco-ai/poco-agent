import type { LucideIcon } from "lucide-react";

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
  enabled: boolean;
  key: string;
  useCustomBaseUrl: boolean;
  baseUrl: string;
};
