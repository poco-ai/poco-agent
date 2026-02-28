import type {
  McpServer,
  UserMcpInstall,
} from "@/features/capabilities/mcp/types";
import { mcpService } from "@/features/capabilities/mcp/api/mcp-api";
import type {
  UserPluginInstall,
  Plugin,
} from "@/features/capabilities/plugins/types";
import { pluginsService } from "@/features/capabilities/plugins/api/plugins-api";
import type {
  Skill,
  UserSkillInstall,
} from "@/features/capabilities/skills/types";
import { skillsService } from "@/features/capabilities/skills/api/skills-api";
import type { ProjectItem, TaskHistoryItem } from "@/features/projects/types";
import {
  projectsService,
  tasksService,
} from "@/features/projects/api/projects-api";

export interface StartupPreloadState {
  projects: ProjectItem[];
  taskHistory: TaskHistoryItem[];
  mcpServers: McpServer[];
  mcpInstalls: UserMcpInstall[];
  skills: Skill[];
  skillInstalls: UserSkillInstall[];
  plugins: Plugin[];
  pluginInstalls: UserPluginInstall[];
}

export type StartupPreloadKey = keyof StartupPreloadState;

const startupPreloadData: Partial<StartupPreloadState> = {};
const readyKeys = new Set<StartupPreloadKey>();
let preloadPromise: Promise<void> | null = null;

function setPreloadValue<K extends StartupPreloadKey>(
  key: K,
  value: StartupPreloadState[K],
): void {
  startupPreloadData[key] = value;
  readyKeys.add(key);
}

async function loadPreloadKey<K extends StartupPreloadKey>(
  key: K,
  loader: () => Promise<StartupPreloadState[K]>,
): Promise<void> {
  try {
    const result = await loader();
    setPreloadValue(key, result);
  } catch (error) {
    console.warn(`[StartupPreload] Failed to preload ${key}`, error);
  }
}

export function startStartupPreload(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve();
  }

  if (preloadPromise) {
    return preloadPromise;
  }

  preloadPromise = Promise.all([
    loadPreloadKey("projects", () => projectsService.listProjects()),
    loadPreloadKey("taskHistory", () => tasksService.listHistory()),
    loadPreloadKey("mcpServers", () => mcpService.listServers()),
    loadPreloadKey("mcpInstalls", () => mcpService.listInstalls()),
    loadPreloadKey("skills", () => skillsService.listSkills()),
    loadPreloadKey("skillInstalls", () => skillsService.listInstalls()),
    loadPreloadKey("plugins", () => pluginsService.listPlugins()),
    loadPreloadKey("pluginInstalls", () => pluginsService.listInstalls()),
  ]).then(() => undefined);

  return preloadPromise;
}

export function getStartupPreloadPromise(): Promise<void> | null {
  return preloadPromise;
}

export function hasStartupPreloadValue(key: StartupPreloadKey): boolean {
  return readyKeys.has(key);
}

export function getStartupPreloadValue<K extends StartupPreloadKey>(
  key: K,
): StartupPreloadState[K] | null {
  if (!readyKeys.has(key)) {
    return null;
  }

  return startupPreloadData[key] as StartupPreloadState[K];
}

export function invalidateStartupPreloadValue(key: StartupPreloadKey): void {
  readyKeys.delete(key);
  delete startupPreloadData[key];
}

export function invalidateStartupPreloadValues(
  keys: StartupPreloadKey[],
): void {
  keys.forEach((key) => {
    invalidateStartupPreloadValue(key);
  });
}
