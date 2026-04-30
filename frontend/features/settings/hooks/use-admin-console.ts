"use client";

import * as React from "react";
import { toast } from "sonner";

import type {
  McpServerCreateInput,
  McpServerUpdateInput,
} from "@/features/capabilities/mcp/types";
import type {
  PluginCreateInput,
  PluginUpdateInput,
} from "@/features/capabilities/plugins/types";
import type {
  Preset,
  PresetCreateInput,
  PresetUpdateInput,
  PresetVisualOption,
} from "@/features/capabilities/presets/lib/preset-types";
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
  Skill,
  SkillCreateInput,
  SkillUpdateInput,
} from "@/features/capabilities/skills/types";
import {
  adminApi,
  type AdminEnvVar,
  type AdminMcpServer,
  type AdminPlugin,
  type AdminSystemEnvVarCreateInput,
  type AdminSystemEnvVarUpdateInput,
  type RuntimeEnvPolicy,
} from "@/features/settings/api/admin-api";
import type { ModelConfigResponse } from "@/features/settings/types";
import type { UserProfile } from "@/features/user/types";
import type { CustomInstructionsSettings } from "@/features/capabilities/personalization/types";
import { useT } from "@/lib/i18n/client";

interface AdminModelConfigInput {
  default_model: string;
  model_list: string[];
}

type AdminDataScope =
  | "envVars"
  | "modelConfig"
  | "users"
  | "skills"
  | "mcp"
  | "plugins"
  | "slashCommands"
  | "subAgents"
  | "presets"
  | "claudeMd"
  | "runtimeEnvPolicy";

function toErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return fallback;
}

function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

export function useAdminConsole() {
  const { t } = useT("translation");
  const [envVars, setEnvVars] = React.useState<AdminEnvVar[]>([]);
  const [users, setUsers] = React.useState<UserProfile[]>([]);
  const [skills, setSkills] = React.useState<Skill[]>([]);
  const [mcpServers, setMcpServers] = React.useState<AdminMcpServer[]>([]);
  const [plugins, setPlugins] = React.useState<AdminPlugin[]>([]);
  const [slashCommands, setSlashCommands] = React.useState<SlashCommand[]>([]);
  const [subAgents, setSubAgents] = React.useState<SubAgent[]>([]);
  const [presets, setPresets] = React.useState<Preset[]>([]);
  const [presetVisuals, setPresetVisuals] = React.useState<
    PresetVisualOption[]
  >([]);
  const [systemClaudeMd, setSystemClaudeMd] =
    React.useState<CustomInstructionsSettings | null>(null);
  const [runtimeEnvPolicy, setRuntimeEnvPolicy] =
    React.useState<RuntimeEnvPolicy | null>(null);
  const [modelConfig, setModelConfig] =
    React.useState<ModelConfigResponse | null>(null);
  const [loadingScopes, setLoadingScopes] = React.useState<Set<AdminDataScope>>(
    () => new Set(),
  );
  const [loadedScopes, setLoadedScopes] = React.useState<Set<AdminDataScope>>(
    () => new Set(),
  );
  const [failedScopes, setFailedScopes] = React.useState<Set<AdminDataScope>>(
    () => new Set(),
  );
  const [savingScopes, setSavingScopes] = React.useState<Set<string>>(
    () => new Set(),
  );

  const scopeLoaders = React.useMemo<
    Record<AdminDataScope, () => Promise<void>>
  >(
    () => ({
      envVars: async () => {
        setEnvVars(await adminApi.listSystemEnvVars());
      },
      modelConfig: async () => {
        setModelConfig(await adminApi.getModelConfig());
      },
      users: async () => {
        setUsers(await adminApi.listUsers());
      },
      skills: async () => {
        setSkills(await adminApi.listSystemSkills());
      },
      mcp: async () => {
        setMcpServers(await adminApi.listSystemMcpServers());
      },
      plugins: async () => {
        setPlugins(await adminApi.listSystemPlugins());
      },
      slashCommands: async () => {
        setSlashCommands(await adminApi.listSystemSlashCommands());
      },
      subAgents: async () => {
        setSubAgents(await adminApi.listSystemSubAgents());
      },
      presets: async () => {
        const [presetData, presetVisualData] = await Promise.all([
          adminApi.listSystemPresets(),
          adminApi.listSystemPresetVisuals(),
        ]);
        setPresets(presetData);
        setPresetVisuals(presetVisualData);
      },
      claudeMd: async () => {
        setSystemClaudeMd(await adminApi.getSystemClaudeMd());
      },
      runtimeEnvPolicy: async () => {
        setRuntimeEnvPolicy(await adminApi.getRuntimeEnvPolicy());
      },
    }),
    [],
  );

  const loadScopes = React.useCallback(
    async (scopes: AdminDataScope[]) => {
      const uniqueScopes = Array.from(new Set(scopes));
      setLoadingScopes((current) => {
        const next = new Set(current);
        uniqueScopes.forEach((scope) => next.add(scope));
        return next;
      });
      try {
        const results = await Promise.allSettled(
          uniqueScopes.map(async (scope) => {
            await scopeLoaders[scope]();
            return scope;
          }),
        );
        const succeededScopes: AdminDataScope[] = [];
        const failedScopesList: AdminDataScope[] = [];
        const failedErrors: Error[] = [];

        results.forEach((result, index) => {
          const scope = uniqueScopes[index];
          if (result.status === "fulfilled") {
            succeededScopes.push(scope);
            return;
          }
          failedScopesList.push(scope);
          failedErrors.push(toError(result.reason));
        });

        if (succeededScopes.length > 0) {
          setLoadedScopes((current) => {
            const next = new Set(current);
            succeededScopes.forEach((scope) => next.add(scope));
            return next;
          });
        }

        setFailedScopes((current) => {
          const next = new Set(current);
          succeededScopes.forEach((scope) => next.delete(scope));
          failedScopesList.forEach((scope) => next.add(scope));
          return next;
        });

        if (failedErrors.length > 0) {
          throw failedErrors[0];
        }
      } finally {
        setLoadingScopes((current) => {
          const next = new Set(current);
          uniqueScopes.forEach((scope) => next.delete(scope));
          return next;
        });
      }
    },
    [scopeLoaders],
  );

  const loadAllData = React.useCallback(async () => {
    try {
      await loadScopes([
        "envVars",
        "modelConfig",
        "users",
        "skills",
        "mcp",
        "plugins",
        "slashCommands",
        "subAgents",
        "presets",
        "claudeMd",
        "runtimeEnvPolicy",
      ]);
    } catch (error) {
      console.error("[useAdminConsole] Failed to load data", error);
      toast.error(t("settings.admin.loadFailed"));
    }
  }, [loadScopes, t]);

  React.useEffect(() => {
    void loadAllData();
  }, [loadAllData]);

  const runAction = React.useCallback(
    async (
      action: () => Promise<void>,
      successMessage: string,
      scope: string,
      reloadScopes: AdminDataScope[],
    ) => {
      setSavingScopes((current) => {
        const next = new Set(current);
        next.add(scope);
        return next;
      });
      try {
        try {
          await action();
        } catch (error) {
          console.error("[useAdminConsole] Action failed", error);
          toast.error(toErrorMessage(error, t("settings.admin.actionFailed")));
          throw error;
        }

        try {
          await loadScopes(reloadScopes);
          toast.success(successMessage);
        } catch (error) {
          console.error("[useAdminConsole] Reload after action failed", error);
          toast.warning(t("settings.admin.reloadFailed"));
        }
      } finally {
        setSavingScopes((current) => {
          const next = new Set(current);
          next.delete(scope);
          return next;
        });
      }
    },
    [loadScopes, t],
  );

  const isSavingScope = React.useCallback(
    (scope: string) => savingScopes.has(scope),
    [savingScopes],
  );

  const isLoadingScope = React.useCallback(
    (scope: AdminDataScope) =>
      loadingScopes.has(scope) ||
      (!loadedScopes.has(scope) && !failedScopes.has(scope)),
    [failedScopes, loadedScopes, loadingScopes],
  );

  const hasErrorScope = React.useCallback(
    (scope: AdminDataScope) => failedScopes.has(scope),
    [failedScopes],
  );

  const refresh = React.useCallback(() => {
    void loadAllData();
  }, [loadAllData]);

  const refreshScope = React.useCallback(
    (scope: AdminDataScope) => {
      void loadScopes([scope]).catch((error) => {
        console.error("[useAdminConsole] Failed to refresh scope", error);
        toast.error(t("settings.admin.loadFailed"));
      });
    },
    [loadScopes, t],
  );

  const saveModelConfig = React.useCallback(
    async (input: AdminModelConfigInput) => {
      await runAction(
        async () => {
          const result = await adminApi.updateModelConfig(input);
          setModelConfig(result);
        },
        t("settings.admin.modelConfigSaved"),
        "modelConfig",
        ["modelConfig"],
      );
    },
    [runAction, t],
  );

  const createEnvVar = React.useCallback(
    async (input: AdminSystemEnvVarCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemEnvVar(input);
        },
        t("settings.admin.envCreated"),
        "envVars",
        ["envVars"],
      );
    },
    [runAction, t],
  );

  const updateEnvVar = React.useCallback(
    async (envVarId: number, input: AdminSystemEnvVarUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemEnvVar(envVarId, input);
        },
        t("settings.admin.envUpdated"),
        "envVars",
        ["envVars"],
      );
    },
    [runAction, t],
  );

  const deleteEnvVar = React.useCallback(
    async (envVarId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemEnvVar(envVarId);
        },
        t("settings.admin.envDeleted"),
        "envVars",
        ["envVars"],
      );
    },
    [runAction, t],
  );

  const saveRuntimeEnvPolicy = React.useCallback(
    async (
      input: Pick<
        RuntimeEnvPolicy,
        "mode" | "allowlist_patterns" | "denylist_patterns"
      >,
    ) => {
      await runAction(
        async () => {
          const result = await adminApi.updateRuntimeEnvPolicy(input);
          setRuntimeEnvPolicy(result);
        },
        t("settings.admin.runtimeEnvPolicySaved"),
        "runtimeEnvPolicy",
        ["runtimeEnvPolicy"],
      );
    },
    [runAction, t],
  );

  const createSkill = React.useCallback(
    async (input: SkillCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemSkill(input);
        },
        t("settings.admin.skillCreated"),
        "skills",
        ["skills"],
      );
    },
    [runAction, t],
  );

  const updateSkill = React.useCallback(
    async (skillId: number, input: SkillUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemSkill(skillId, input);
        },
        t("settings.admin.skillUpdated"),
        "skills",
        ["skills"],
      );
    },
    [runAction, t],
  );

  const deleteSkill = React.useCallback(
    async (skillId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemSkill(skillId);
        },
        t("settings.admin.skillDeleted"),
        "skills",
        ["skills"],
      );
    },
    [runAction, t],
  );

  const createMcpServer = React.useCallback(
    async (input: McpServerCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemMcpServer(input);
        },
        t("settings.admin.mcpCreated"),
        "mcp",
        ["mcp"],
      );
    },
    [runAction, t],
  );

  const updateMcpServer = React.useCallback(
    async (serverId: number, input: McpServerUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemMcpServer(serverId, input);
        },
        t("settings.admin.mcpUpdated"),
        "mcp",
        ["mcp"],
      );
    },
    [runAction, t],
  );

  const deleteMcpServer = React.useCallback(
    async (serverId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemMcpServer(serverId);
        },
        t("settings.admin.mcpDeleted"),
        "mcp",
        ["mcp"],
      );
    },
    [runAction, t],
  );

  const createPlugin = React.useCallback(
    async (input: PluginCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemPlugin(input);
        },
        t("settings.admin.pluginCreated"),
        "plugins",
        ["plugins"],
      );
    },
    [runAction, t],
  );

  const updatePlugin = React.useCallback(
    async (pluginId: number, input: PluginUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemPlugin(pluginId, input);
        },
        t("settings.admin.pluginUpdated"),
        "plugins",
        ["plugins"],
      );
    },
    [runAction, t],
  );

  const deletePlugin = React.useCallback(
    async (pluginId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemPlugin(pluginId);
        },
        t("settings.admin.pluginDeleted"),
        "plugins",
        ["plugins"],
      );
    },
    [runAction, t],
  );

  const createSlashCommand = React.useCallback(
    async (input: SlashCommandCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemSlashCommand(input);
        },
        t("settings.admin.slashCommandCreated"),
        "slashCommands",
        ["slashCommands"],
      );
    },
    [runAction, t],
  );

  const updateSlashCommand = React.useCallback(
    async (commandId: number, input: SlashCommandUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemSlashCommand(commandId, input);
        },
        t("settings.admin.slashCommandUpdated"),
        "slashCommands",
        ["slashCommands"],
      );
    },
    [runAction, t],
  );

  const deleteSlashCommand = React.useCallback(
    async (commandId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemSlashCommand(commandId);
        },
        t("settings.admin.slashCommandDeleted"),
        "slashCommands",
        ["slashCommands"],
      );
    },
    [runAction, t],
  );

  const saveSystemClaudeMd = React.useCallback(
    async (input: { enabled: boolean; content: string }) => {
      await runAction(
        async () => {
          const result = await adminApi.updateSystemClaudeMd(input);
          setSystemClaudeMd(result);
        },
        t("settings.admin.claudeMdSaved"),
        "claudeMd",
        ["claudeMd"],
      );
    },
    [runAction, t],
  );

  const deleteSystemClaudeMd = React.useCallback(async () => {
    await runAction(
      async () => {
        await adminApi.deleteSystemClaudeMd();
        setSystemClaudeMd({ enabled: false, content: "", updated_at: null });
      },
      t("settings.admin.claudeMdDeleted"),
      "claudeMd",
      ["claudeMd"],
    );
  }, [runAction, t]);

  const createSubAgent = React.useCallback(
    async (input: SubAgentCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemSubAgent(input);
        },
        t("settings.admin.subAgentCreated"),
        "subAgents",
        ["subAgents"],
      );
    },
    [runAction, t],
  );

  const updateSubAgent = React.useCallback(
    async (subAgentId: number, input: SubAgentUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemSubAgent(subAgentId, input);
        },
        t("settings.admin.subAgentUpdated"),
        "subAgents",
        ["subAgents"],
      );
    },
    [runAction, t],
  );

  const deleteSubAgent = React.useCallback(
    async (subAgentId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemSubAgent(subAgentId);
        },
        t("settings.admin.subAgentDeleted"),
        "subAgents",
        ["subAgents"],
      );
    },
    [runAction, t],
  );

  const createPreset = React.useCallback(
    async (input: PresetCreateInput) => {
      await runAction(
        async () => {
          await adminApi.createSystemPreset(input);
        },
        t("settings.admin.presetCreated"),
        "presets",
        ["presets"],
      );
    },
    [runAction, t],
  );

  const updatePreset = React.useCallback(
    async (presetId: number, input: PresetUpdateInput) => {
      await runAction(
        async () => {
          await adminApi.updateSystemPreset(presetId, input);
        },
        t("settings.admin.presetUpdated"),
        "presets",
        ["presets"],
      );
    },
    [runAction, t],
  );

  const deletePreset = React.useCallback(
    async (presetId: number) => {
      await runAction(
        async () => {
          await adminApi.deleteSystemPreset(presetId);
        },
        t("settings.admin.presetDeleted"),
        "presets",
        ["presets"],
      );
    },
    [runAction, t],
  );

  const updateUserRole = React.useCallback(
    async (userId: string, systemRole: "user" | "admin") => {
      await runAction(
        async () => {
          await adminApi.updateUserSystemRole(userId, {
            system_role: systemRole,
          });
        },
        t("settings.admin.userRoleUpdated"),
        "users",
        ["users"],
      );
    },
    [runAction, t],
  );

  return {
    envVars,
    users,
    skills,
    mcpServers,
    plugins,
    slashCommands,
    subAgents,
    presets,
    presetVisuals,
    systemClaudeMd,
    runtimeEnvPolicy,
    modelConfig,
    isLoadingScope,
    hasErrorScope,
    isSavingScope,
    refresh,
    refreshScope,
    saveModelConfig,
    createEnvVar,
    updateEnvVar,
    deleteEnvVar,
    saveRuntimeEnvPolicy,
    createSkill,
    updateSkill,
    deleteSkill,
    createMcpServer,
    updateMcpServer,
    deleteMcpServer,
    createPlugin,
    updatePlugin,
    deletePlugin,
    createSlashCommand,
    updateSlashCommand,
    deleteSlashCommand,
    createSubAgent,
    updateSubAgent,
    deleteSubAgent,
    createPreset,
    updatePreset,
    deletePreset,
    saveSystemClaudeMd,
    deleteSystemClaudeMd,
    updateUserRole,
  };
}
