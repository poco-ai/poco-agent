import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  Preset,
  PresetCopyInput,
  PresetCreateInput,
  PresetVisualOption,
  PresetUpdateInput,
} from "@/features/capabilities/presets/lib/preset-types";

export const presetsService = {
  listPresets: async (options?: { revalidate?: number }): Promise<Preset[]> => {
    return apiClient.get<Preset[]>(API_ENDPOINTS.presets, {
      next: { revalidate: options?.revalidate },
    });
  },

  listPresetVisuals: async (options?: {
    revalidate?: number;
  }): Promise<PresetVisualOption[]> => {
    return apiClient.get<PresetVisualOption[]>(API_ENDPOINTS.presetVisuals, {
      next: { revalidate: options?.revalidate },
    });
  },

  getPreset: async (
    presetId: number,
    options?: { revalidate?: number },
  ): Promise<Preset> => {
    return apiClient.get<Preset>(API_ENDPOINTS.preset(presetId), {
      next: { revalidate: options?.revalidate },
    });
  },

  createPreset: async (input: PresetCreateInput): Promise<Preset> => {
    return apiClient.post<Preset>(API_ENDPOINTS.presets, input);
  },

  updatePreset: async (
    presetId: number,
    input: PresetUpdateInput,
  ): Promise<Preset> => {
    return apiClient.put<Preset>(API_ENDPOINTS.preset(presetId), input);
  },

  deletePreset: async (presetId: number): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.preset(presetId),
    );
  },

  copyPreset: async (presetId: number, input: PresetCopyInput): Promise<Preset> => {
    return apiClient.post<Preset>(API_ENDPOINTS.presetCopy(presetId), input);
  },

  list: async (options?: { revalidate?: number }) =>
    presetsService.listPresets(options),
};
