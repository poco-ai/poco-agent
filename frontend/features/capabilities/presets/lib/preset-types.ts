export type PresetSubAgentModel = "sonnet" | "opus" | "haiku" | "inherit";

export interface PresetSubAgentConfig {
  name: string;
  description?: string | null;
  prompt?: string | null;
  model?: PresetSubAgentModel | null;
  tools?: string[] | null;
}

export interface PresetVisualOption {
  key: string;
  name?: string | null;
  url?: string | null;
  version?: string | null;
}

export interface Preset {
  preset_id: number;
  user_id: string;
  name: string;
  description?: string | null;
  visual_key: string;
  visual_url?: string | null;
  visual_version?: string | null;
  visual_name?: string | null;
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
  visual_key: string;
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
  visual_key?: string | null;
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
