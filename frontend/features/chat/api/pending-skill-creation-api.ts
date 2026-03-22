import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  PendingSkillCreation,
  PendingSkillCreationCancelInput,
  PendingSkillCreationConfirmInput,
} from "@/features/chat/types";

export const pendingSkillCreationService = {
  listPending: async (
    sessionId?: string | null,
  ): Promise<PendingSkillCreation[]> => {
    if (!sessionId) {
      return apiClient.get<PendingSkillCreation[]>(
        API_ENDPOINTS.pendingSkillCreations,
      );
    }
    const params = new URLSearchParams({ session_id: sessionId });
    return apiClient.get<PendingSkillCreation[]>(
      `${API_ENDPOINTS.pendingSkillCreations}?${params.toString()}`,
      { cache: "no-store" },
    );
  },

  getById: async (creationId: string): Promise<PendingSkillCreation> => {
    return apiClient.get<PendingSkillCreation>(
      API_ENDPOINTS.pendingSkillCreation(creationId),
      { cache: "no-store" },
    );
  },

  confirm: async (
    creationId: string,
    payload: PendingSkillCreationConfirmInput,
  ): Promise<PendingSkillCreation> => {
    return apiClient.post<PendingSkillCreation>(
      API_ENDPOINTS.pendingSkillCreationConfirm(creationId),
      payload,
    );
  },

  cancel: async (
    creationId: string,
    payload?: PendingSkillCreationCancelInput,
  ): Promise<PendingSkillCreation> => {
    return apiClient.post<PendingSkillCreation>(
      API_ENDPOINTS.pendingSkillCreationCancel(creationId),
      payload ?? {},
    );
  },
};
