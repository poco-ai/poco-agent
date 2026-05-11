"use client";

import {
  createContext,
  useContext,
  useCallback,
  useState,
  useRef,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import type { McpServer } from "@/features/capabilities/mcp/types";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import type { Skill } from "@/features/capabilities/skills/types";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import { getEffectiveInstallState } from "@/features/capabilities/lib/install-policy";
import {
  getStartupPreloadValue,
  hasStartupPreloadValue,
} from "@/lib/startup-preload";

function toSkillEnabledMap(
  skills: Skill[] | null,
  installs: Array<{ skill_id: number; enabled: boolean }> | null,
): Record<number, boolean> {
  const result: Record<number, boolean> = {};
  const installsBySkillId = new Map<
    number,
    { skill_id: number; enabled: boolean }
  >();
  for (const install of installs ?? []) {
    installsBySkillId.set(install.skill_id, install);
  }
  for (const skill of skills ?? []) {
    const install = installsBySkillId.get(skill.id);
    result[skill.id] = getEffectiveInstallState(
      skill,
      install
        ? {
            id: install.skill_id,
            enabled: install.enabled,
          }
        : null,
    ).isEnabled;
  }
  return result;
}

function toEffectiveMcpEnabledMap(
  servers: McpServer[] | null,
  installs: Array<{ server_id: number; enabled: boolean }> | null,
): Record<number, boolean> {
  const result: Record<number, boolean> = {};
  const installsByServerId = new Map<
    number,
    { server_id: number; enabled: boolean }
  >();
  for (const install of installs ?? []) {
    installsByServerId.set(install.server_id, install);
  }
  for (const server of servers ?? []) {
    const install = installsByServerId.get(server.id);
    result[server.id] = getEffectiveInstallState(
      server,
      install
        ? {
            id: install.server_id,
            enabled: install.enabled,
          }
        : null,
    ).isEnabled;
  }
  return result;
}

interface CapabilityToggleContextValue {
  mcpEnabledMap: Record<number, boolean>;
  skillEnabledMap: Record<number, boolean>;
  mcpOverrideMap: Record<number, boolean>;
  skillOverrideMap: Record<number, boolean>;
  isLoading: boolean;
  hasFetched: boolean;

  toggleMcp: (serverId: number, enabled: boolean) => void;
  toggleSkill: (skillId: number, enabled: boolean) => void;
}

const CapabilityToggleContext =
  createContext<CapabilityToggleContextValue | null>(null);

/**
 * Hook to access the capability toggle context.
 * Returns null if used outside of CapabilityToggleProvider.
 */
export function useCapabilityToggle() {
  return useContext(CapabilityToggleContext);
}

interface CapabilityToggleProviderProps {
  children: ReactNode;
}

export function CapabilityToggleProvider({
  children,
}: CapabilityToggleProviderProps) {
  const preloadedMcpInstalls = hasStartupPreloadValue("mcpInstalls")
    ? getStartupPreloadValue("mcpInstalls")
    : null;
  const preloadedMcpServers = hasStartupPreloadValue("mcpServers")
    ? getStartupPreloadValue("mcpServers")
    : null;
  const preloadedSkills = hasStartupPreloadValue("skills")
    ? getStartupPreloadValue("skills")
    : null;
  const preloadedSkillInstalls = hasStartupPreloadValue("skillInstalls")
    ? getStartupPreloadValue("skillInstalls")
    : null;
  const hasPreloadedState = Boolean(
    preloadedMcpInstalls &&
    preloadedSkillInstalls &&
    preloadedMcpServers &&
    preloadedSkills,
  );
  const [baseMcpEnabledMap, setBaseMcpEnabledMap] = useState<
    Record<number, boolean>
  >(() => toEffectiveMcpEnabledMap(preloadedMcpServers, preloadedMcpInstalls));
  const [baseSkillEnabledMap, setBaseSkillEnabledMap] = useState<
    Record<number, boolean>
  >(() => toSkillEnabledMap(preloadedSkills, preloadedSkillInstalls));
  const [mcpOverrideMap, setMcpOverrideMap] = useState<Record<number, boolean>>(
    {},
  );
  const [skillOverrideMap, setSkillOverrideMap] = useState<
    Record<number, boolean>
  >({});
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(hasPreloadedState);
  const didInitialFetchRef = useRef(false);

  const refreshFromApi = useCallback(async () => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const [mcpServers, mcpInstalls, skills, skillInstalls] =
        await Promise.all([
          mcpService.listServers(),
          mcpService.listInstalls(),
          skillsService.listSkills(),
          skillsService.listInstalls(),
        ]);

      setBaseMcpEnabledMap(toEffectiveMcpEnabledMap(mcpServers, mcpInstalls));
      setBaseSkillEnabledMap(toSkillEnabledMap(skills, skillInstalls));
      setHasFetched(true);
    } catch (error) {
      console.error("[CapabilityToggleContext] Failed to fetch data:", error);
    } finally {
      setIsLoading(false);
    }
  }, [isLoading]);

  useEffect(() => {
    if (didInitialFetchRef.current) return;
    didInitialFetchRef.current = true;
    void refreshFromApi();
  }, [refreshFromApi]);

  const toggleMcp = useCallback(
    (serverId: number, enabled: boolean) => {
      setMcpOverrideMap((prev) => {
        const baseEnabled = baseMcpEnabledMap[serverId];
        if (enabled === baseEnabled) {
          const next = { ...prev };
          delete next[serverId];
          return next;
        }
        return {
          ...prev,
          [serverId]: enabled,
        };
      });
    },
    [baseMcpEnabledMap],
  );

  const toggleSkill = useCallback(
    (skillId: number, enabled: boolean) => {
      setSkillOverrideMap((prev) => {
        const baseEnabled = baseSkillEnabledMap[skillId];
        if (enabled === baseEnabled) {
          const next = { ...prev };
          delete next[skillId];
          return next;
        }
        return {
          ...prev,
          [skillId]: enabled,
        };
      });
    },
    [baseSkillEnabledMap],
  );

  const mcpEnabledMap = useMemo(
    () => ({
      ...baseMcpEnabledMap,
      ...mcpOverrideMap,
    }),
    [baseMcpEnabledMap, mcpOverrideMap],
  );

  const skillEnabledMap = useMemo(
    () => ({
      ...baseSkillEnabledMap,
      ...skillOverrideMap,
    }),
    [baseSkillEnabledMap, skillOverrideMap],
  );

  const value: CapabilityToggleContextValue = {
    mcpEnabledMap,
    skillEnabledMap,
    mcpOverrideMap,
    skillOverrideMap,
    isLoading,
    hasFetched,
    toggleMcp,
    toggleSkill,
  };

  return (
    <CapabilityToggleContext.Provider value={value}>
      {children}
    </CapabilityToggleContext.Provider>
  );
}
