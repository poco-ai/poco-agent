export type PresetIcon =
  | "default"
  | "code"
  | "branch"
  | "database"
  | "globe"
  | "paintbrush"
  | "book"
  | "chip"
  | "robot"
  | "file"
  | "message"
  | "chart"
  | "shield"
  | "terminal"
  | "zap"
  | "pen"
  | "wrench"
  | "link"
  | "cpu"
  | "search"
  | "mail"
  | "image"
  | "folder"
  | "clipboard"
  | "bug"
  | "cloud"
  | "rocket"
  | "target";

export type PresetSubAgentModel = "sonnet" | "opus" | "haiku" | "inherit";

export interface PresetSubAgentConfig {
  name: string;
  description?: string | null;
  prompt?: string | null;
  model?: PresetSubAgentModel | null;
  tools?: string[] | null;
}

export interface Preset {
  preset_id: number;
  user_id: string;
  name: string;
  description?: string | null;
  icon: PresetIcon;
  color?: string | null;
  prompt_template?: string | null;
  browser_enabled: boolean;
  memory_enabled: boolean;
  skill_ids: number[];
  mcp_server_ids: number[];
  plugin_ids: number[];
  subagent_configs: PresetSubAgentConfig[];
  created_at: string;
  updated_at: string;
}

export interface PresetCreateInput {
  name: string;
  description?: string | null;
  icon?: PresetIcon;
  color?: string | null;
  prompt_template?: string | null;
  browser_enabled?: boolean;
  memory_enabled?: boolean;
  skill_ids?: number[];
  mcp_server_ids?: number[];
  plugin_ids?: number[];
  subagent_configs?: PresetSubAgentConfig[];
}

export interface PresetUpdateInput {
  name?: string | null;
  description?: string | null;
  icon?: PresetIcon | null;
  color?: string | null;
  prompt_template?: string | null;
  browser_enabled?: boolean | null;
  memory_enabled?: boolean | null;
  skill_ids?: number[] | null;
  mcp_server_ids?: number[] | null;
  plugin_ids?: number[] | null;
  subagent_configs?: PresetSubAgentConfig[] | null;
}

export interface PresetCapabilityItem {
  id: number;
  name: string;
  description?: string | null;
  scope?: string | null;
}
