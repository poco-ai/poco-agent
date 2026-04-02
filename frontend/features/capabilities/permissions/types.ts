export interface PermissionRuleMatch {
  tools?: string[] | null;
  tool_categories?: string[] | null;
  path_patterns?: string[] | null;
  network_patterns?: string[] | null;
  mcp_servers?: string[] | null;
}

export interface PermissionRule {
  id: string;
  priority: number;
  match: PermissionRuleMatch;
  action: "allow" | "deny" | "ask";
  reason: string;
  enabled: boolean;
}

export interface PermissionPolicy {
  version: string;
  mode: "audit" | "enforce";
  default_action: "allow" | "deny";
  preset_source?: string | null;
  rules: PermissionRule[];
}

export const DEFAULT_POLICY: PermissionPolicy = {
  version: "v1",
  mode: "audit",
  default_action: "allow",
  preset_source: null,
  rules: [],
};

export const TOOL_CATEGORIES = [
  "read",
  "write",
  "execute",
  "network",
  "mcp",
] as const;

export const PRESET_SOURCES = [
  "default",
  "acceptEdits",
  "plan",
  "bypassPermissions",
] as const;
