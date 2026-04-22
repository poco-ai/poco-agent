import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  EnvVarCreateInput,
  EnvVarUpdateInput,
} from "@/features/capabilities/env-vars/types";
import type {
  Skill,
  SkillCreateInput,
  SkillImportCommitInput,
  SkillImportCommitEnqueueResponse,
  SkillImportDiscoverResponse,
  SkillImportJobStatusResponse,
  SkillUpdateInput,
} from "@/features/capabilities/skills/types";
import type {
  McpServerCreateInput,
  McpServerUpdateInput,
} from "@/features/capabilities/mcp/types";
import type {
  PluginCreateInput,
  PluginImportCommitInput,
  PluginImportCommitEnqueueResponse,
  PluginImportDiscoverResponse,
  PluginImportJobStatusResponse,
  PluginUpdateInput,
} from "@/features/capabilities/plugins/types";
import type {
  SlashCommand,
  SlashCommandCreateInput,
  SlashCommandUpdateInput,
} from "@/features/capabilities/slash-commands/types";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentUpdateInput,
} from "@/features/capabilities/sub-agents/types";
import type {
  Preset,
  PresetCreateInput,
  PresetUpdateInput,
  PresetVisualOption,
} from "@/features/capabilities/presets/lib/preset-types";
import type { UserProfile } from "@/features/user/types";
import type { ModelConfigResponse } from "@/features/settings/types";
import type {
  CustomInstructionsSettings,
  CustomInstructionsUpsertInput,
} from "@/features/capabilities/personalization/types";

interface AdminUserResponse {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  system_role: "user" | "admin";
  created_at: string;
}

function mapAdminUser(payload: AdminUserResponse): UserProfile {
  return {
    id: payload.id,
    email: payload.email,
    displayName: payload.display_name,
    avatar: payload.avatar_url,
    systemRole: payload.system_role,
    plan: "free",
    planName: "user.plan.free",
  };
}

export interface AdminEnvVar {
  id: number;
  user_id: string;
  key: string;
  description: string | null;
  scope: "system" | "user";
  is_set: boolean;
  masked_value: string;
  created_at: string;
  updated_at: string;
}

export interface AdminMcpServer {
  id: number;
  name: string;
  description: string | null;
  server_config: Record<string, unknown>;
  masked_server_config: Record<string, unknown>;
  has_sensitive_data: boolean;
  scope: string;
  owner_user_id: string | null;
  default_enabled: boolean;
  force_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminPlugin {
  id: number;
  name: string;
  masked_entry: Record<string, unknown>;
  masked_manifest: Record<string, unknown> | null;
  entry_has_sensitive_data: boolean;
  manifest_has_sensitive_data: boolean;
  scope: string;
  owner_user_id: string | null;
  default_enabled: boolean;
  force_enabled: boolean;
  description: string | null;
  version: string | null;
  created_at: string;
  updated_at: string;
}

export interface AdminModelConfigUpdateInput {
  default_model: string;
  model_list: string[];
}

export interface AdminUserRoleUpdateInput {
  system_role: "user" | "admin";
}

export const adminApi = {
  listSystemEnvVars: async (): Promise<AdminEnvVar[]> => {
    return apiClient.get<AdminEnvVar[]>(API_ENDPOINTS.adminSystemEnvVars, {
      cache: "no-store",
    });
  },
  createSystemEnvVar: async (input: EnvVarCreateInput) => {
    return apiClient.post(API_ENDPOINTS.adminSystemEnvVars, input);
  },
  updateSystemEnvVar: async (envVarId: number, input: EnvVarUpdateInput) => {
    return apiClient.patch(API_ENDPOINTS.adminSystemEnvVar(envVarId), input);
  },
  deleteSystemEnvVar: async (envVarId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminSystemEnvVar(envVarId));
  },
  getModelConfig: async (): Promise<ModelConfigResponse> => {
    return apiClient.get<ModelConfigResponse>(API_ENDPOINTS.adminModelConfig, {
      cache: "no-store",
    });
  },
  updateModelConfig: async (
    input: AdminModelConfigUpdateInput,
  ): Promise<ModelConfigResponse> => {
    return apiClient.patch<ModelConfigResponse>(
      API_ENDPOINTS.adminModelConfig,
      input,
    );
  },
  listSystemSkills: async (): Promise<Skill[]> => {
    return apiClient.get<Skill[]>(API_ENDPOINTS.adminSkills, {
      cache: "no-store",
    });
  },
  createSystemSkill: async (input: SkillCreateInput): Promise<Skill> => {
    return apiClient.post<Skill>(API_ENDPOINTS.adminSkills, input);
  },
  updateSystemSkill: async (
    skillId: number,
    input: SkillUpdateInput,
  ): Promise<Skill> => {
    return apiClient.patch<Skill>(API_ENDPOINTS.adminSkill(skillId), input);
  },
  deleteSystemSkill: async (skillId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminSkill(skillId));
  },
  importSystemSkillDiscover: async (
    formData: FormData,
  ): Promise<SkillImportDiscoverResponse> => {
    return apiClient.post<SkillImportDiscoverResponse>(
      API_ENDPOINTS.adminSkillImportDiscover,
      formData,
      { timeoutMs: 5 * 60_000 },
    );
  },
  importSystemSkillCommit: async (
    input: SkillImportCommitInput,
  ): Promise<SkillImportCommitEnqueueResponse> => {
    return apiClient.post<SkillImportCommitEnqueueResponse>(
      API_ENDPOINTS.adminSkillImportCommit,
      input,
    );
  },
  getSystemSkillImportJob: async (
    jobId: string,
  ): Promise<SkillImportJobStatusResponse> => {
    return apiClient.get<SkillImportJobStatusResponse>(
      API_ENDPOINTS.adminSkillImportJob(jobId),
      { cache: "no-store" },
    );
  },
  listSystemMcpServers: async (): Promise<AdminMcpServer[]> => {
    return apiClient.get<AdminMcpServer[]>(API_ENDPOINTS.adminMcpServers, {
      cache: "no-store",
    });
  },
  createSystemMcpServer: async (
    input: McpServerCreateInput,
  ): Promise<AdminMcpServer> => {
    return apiClient.post<AdminMcpServer>(API_ENDPOINTS.adminMcpServers, input);
  },
  updateSystemMcpServer: async (
    serverId: number,
    input: McpServerUpdateInput,
  ): Promise<AdminMcpServer> => {
    return apiClient.patch<AdminMcpServer>(
      API_ENDPOINTS.adminMcpServer(serverId),
      input,
    );
  },
  deleteSystemMcpServer: async (serverId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminMcpServer(serverId));
  },
  listSystemPlugins: async (): Promise<AdminPlugin[]> => {
    return apiClient.get<AdminPlugin[]>(API_ENDPOINTS.adminPlugins, {
      cache: "no-store",
    });
  },
  createSystemPlugin: async (
    input: PluginCreateInput,
  ): Promise<AdminPlugin> => {
    return apiClient.post<AdminPlugin>(API_ENDPOINTS.adminPlugins, input);
  },
  updateSystemPlugin: async (
    pluginId: number,
    input: PluginUpdateInput,
  ): Promise<AdminPlugin> => {
    return apiClient.patch<AdminPlugin>(
      API_ENDPOINTS.adminPlugin(pluginId),
      input,
    );
  },
  deleteSystemPlugin: async (pluginId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminPlugin(pluginId));
  },
  importSystemPluginDiscover: async (
    formData: FormData,
  ): Promise<PluginImportDiscoverResponse> => {
    return apiClient.post<PluginImportDiscoverResponse>(
      API_ENDPOINTS.adminPluginImportDiscover,
      formData,
      { timeoutMs: 5 * 60_000 },
    );
  },
  importSystemPluginCommit: async (
    input: PluginImportCommitInput,
  ): Promise<PluginImportCommitEnqueueResponse> => {
    return apiClient.post<PluginImportCommitEnqueueResponse>(
      API_ENDPOINTS.adminPluginImportCommit,
      input,
    );
  },
  getSystemPluginImportJob: async (
    jobId: string,
  ): Promise<PluginImportJobStatusResponse> => {
    return apiClient.get<PluginImportJobStatusResponse>(
      API_ENDPOINTS.adminPluginImportJob(jobId),
      { cache: "no-store" },
    );
  },
  listSystemSlashCommands: async (): Promise<AdminSlashCommand[]> => {
    return apiClient.get<AdminSlashCommand[]>(
      API_ENDPOINTS.adminSlashCommands,
      {
        cache: "no-store",
      },
    );
  },
  createSystemSlashCommand: async (
    input: SlashCommandCreateInput,
  ): Promise<AdminSlashCommand> => {
    return apiClient.post<AdminSlashCommand>(
      API_ENDPOINTS.adminSlashCommands,
      input,
    );
  },
  updateSystemSlashCommand: async (
    commandId: number,
    input: SlashCommandUpdateInput,
  ): Promise<AdminSlashCommand> => {
    return apiClient.patch<AdminSlashCommand>(
      API_ENDPOINTS.adminSlashCommand(commandId),
      input,
    );
  },
  deleteSystemSlashCommand: async (commandId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminSlashCommand(commandId));
  },
  getSystemClaudeMd: async (): Promise<CustomInstructionsSettings> => {
    return apiClient.get<CustomInstructionsSettings>(
      API_ENDPOINTS.adminClaudeMd,
      {
        cache: "no-store",
      },
    );
  },
  updateSystemClaudeMd: async (
    input: CustomInstructionsUpsertInput,
  ): Promise<CustomInstructionsSettings> => {
    return apiClient.put<CustomInstructionsSettings>(
      API_ENDPOINTS.adminClaudeMd,
      input,
    );
  },
  deleteSystemClaudeMd: async () => {
    return apiClient.delete(API_ENDPOINTS.adminClaudeMd);
  },
  listSystemSubAgents: async (): Promise<SubAgent[]> => {
    return apiClient.get<SubAgent[]>(API_ENDPOINTS.adminSubAgents, {
      cache: "no-store",
    });
  },
  createSystemSubAgent: async (
    input: SubAgentCreateInput,
  ): Promise<SubAgent> => {
    return apiClient.post<SubAgent>(API_ENDPOINTS.adminSubAgents, input);
  },
  updateSystemSubAgent: async (
    subAgentId: number,
    input: SubAgentUpdateInput,
  ): Promise<SubAgent> => {
    return apiClient.patch<SubAgent>(
      API_ENDPOINTS.adminSubAgent(subAgentId),
      input,
    );
  },
  deleteSystemSubAgent: async (subAgentId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminSubAgent(subAgentId));
  },
  listSystemPresetVisuals: async (): Promise<PresetVisualOption[]> => {
    return apiClient.get<PresetVisualOption[]>(
      API_ENDPOINTS.adminPresetVisuals,
      {
        cache: "no-store",
      },
    );
  },
  listSystemPresets: async (): Promise<Preset[]> => {
    return apiClient.get<Preset[]>(API_ENDPOINTS.adminPresets, {
      cache: "no-store",
    });
  },
  createSystemPreset: async (input: PresetCreateInput): Promise<Preset> => {
    return apiClient.post<Preset>(API_ENDPOINTS.adminPresets, input);
  },
  updateSystemPreset: async (
    presetId: number,
    input: PresetUpdateInput,
  ): Promise<Preset> => {
    return apiClient.put<Preset>(API_ENDPOINTS.adminPreset(presetId), input);
  },
  deleteSystemPreset: async (presetId: number) => {
    return apiClient.delete(API_ENDPOINTS.adminPreset(presetId));
  },
  listUsers: async (): Promise<UserProfile[]> => {
    const users = await apiClient.get<AdminUserResponse[]>(
      API_ENDPOINTS.adminUsers,
      { cache: "no-store" },
    );
    return users.map(mapAdminUser);
  },
  updateUserSystemRole: async (
    userId: string,
    input: AdminUserRoleUpdateInput,
  ): Promise<UserProfile> => {
    const user = await apiClient.patch<AdminUserResponse>(
      API_ENDPOINTS.adminUserSystemRole(userId),
      input,
    );
    return mapAdminUser(user);
  },
};

export type AdminSlashCommand = SlashCommand;
