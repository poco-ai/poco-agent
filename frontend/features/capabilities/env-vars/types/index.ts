export type EnvVarScope = "system" | "user";

export interface EnvVar {
  id: number;
  user_id: string;
  key: string;
  // Public API will never return plaintext values. Keep optional for backward compatibility
  // with older components that might still reference it.
  value?: string | null;
  description: string | null;
  scope: EnvVarScope;
  is_set: boolean;
  expose_to_runtime: boolean;
  created_at: string;
  updated_at: string;
}

export interface EnvVarCreateInput {
  key: string;
  value: string;
  description?: string | null;
  expose_to_runtime?: boolean;
}

export interface EnvVarUpdateInput {
  value?: string | null;
  description?: string | null;
  expose_to_runtime?: boolean | null;
}
