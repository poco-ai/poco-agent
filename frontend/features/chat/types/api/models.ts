export type CredentialState = "none" | "system" | "user";
export type BaseUrlSource = "default" | "system" | "user";

export interface ModelDefinition {
  model_id: string;
  display_name: string;
  provider_id: string;
  requires_credentials: boolean;
  supports_custom_base_url: boolean;
}

export interface ModelProvider {
  provider_id: string;
  display_name: string;
  api_key_env_key: string;
  base_url_env_key: string;
  credential_state: CredentialState;
  default_base_url: string;
  effective_base_url: string;
  base_url_source: BaseUrlSource;
  supports_model_discovery: boolean;
  models: ModelDefinition[];
  discovered_models: ModelDefinition[];
}

export interface ModelConfigResponse {
  default_model: string;
  model_list: string[];
  mem0_enabled?: boolean;
  models: ModelDefinition[];
  providers: ModelProvider[];
}

export interface ProviderModelDiscoveryRequest {
  api_key?: string | null;
  base_url?: string | null;
}

export interface ProviderModelDiscoveryResponse {
  provider_id: string;
  models: ModelDefinition[];
}

export interface ProviderModelSettingsUpdateInput {
  model_ids: string[];
}
