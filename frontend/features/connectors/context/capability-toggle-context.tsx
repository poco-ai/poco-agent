"use client";

import {
  createContext,
  useContext,
  useCallback,
  useState,
  useRef,
  useEffect,
  type ReactNode,
} from "react";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import {
  getStartupPreloadValue,
  hasStartupPreloadValue,
} from "@/lib/startup-preload";

function toMcpEnabledMap(
  installs: Array<{ server_id: number; enabled: boolean }> | null,
): Record<number, boolean> {
  const result: Record<number, boolean> = {};
  for (const install of installs ?? []) {
    result[install.server_id] = install.enabled;
  }
  return result;
}

function toSkillEnabledMap(
  installs: Array<{ skill_id: number; enabled: boolean }> | null,
): Record<number, boolean> {
  const result: Record<number, boolean> = {};
  for (const install of installs ?? []) {
    result[install.skill_id] = install.enabled;
  }
  return result;
}

interface CapabilityToggleContextValue {
  mcpEnabledMap: Record<number, boolean>;
  skillEnabledMap: Record<number, boolean>;
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
  const preloadedSkillInstalls = hasStartupPreloadValue("skillInstalls")
    ? getStartupPreloadValue("skillInstalls")
    : null;
  const hasPreloadedState = Boolean(
    preloadedMcpInstalls && preloadedSkillInstalls,
  );
  const [mcpEnabledMap, setMcpEnabledMap] = useState<Record<number, boolean>>(
    () => toMcpEnabledMap(preloadedMcpInstalls),
  );
  const [skillEnabledMap, setSkillEnabledMap] = useState<
    Record<number, boolean>
  >(() => toSkillEnabledMap(preloadedSkillInstalls));
  const [isLoading, setIsLoading] = useState(false);
  const [hasFetched, setHasFetched] = useState(hasPreloadedState);
  const didInitialFetchRef = useRef(false);

  const refreshFromApi = useCallback(async () => {
    if (isLoading) return;
    setIsLoading(true);
    try {
      const [mcpInstalls, skillInstalls] = await Promise.all([
        mcpService.listInstalls(),
        skillsService.listInstalls(),
      ]);

      setMcpEnabledMap(toMcpEnabledMap(mcpInstalls));
      setSkillEnabledMap(toSkillEnabledMap(skillInstalls));
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

  const toggleMcp = useCallback((serverId: number, enabled: boolean) => {
    setMcpEnabledMap((prev) => ({
      ...prev,
      [serverId]: enabled,
    }));
  }, []);

  const toggleSkill = useCallback((skillId: number, enabled: boolean) => {
    setSkillEnabledMap((prev) => ({
      ...prev,
      [skillId]: enabled,
    }));
  }, []);

  const value: CapabilityToggleContextValue = {
    mcpEnabledMap,
    skillEnabledMap,
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
