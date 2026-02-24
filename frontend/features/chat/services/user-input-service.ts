import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  UserInputRequest,
  UserInputAnswerRequest,
} from "@/features/chat/types";

export const userInputService = {
  listPending: async (
    sessionId?: string | null,
  ): Promise<UserInputRequest[]> => {
    if (!sessionId) {
      return apiClient.get<UserInputRequest[]>(API_ENDPOINTS.userInputRequests);
    }
    const params = new URLSearchParams({ session_id: sessionId });
    return apiClient.get<UserInputRequest[]>(
      `${API_ENDPOINTS.userInputRequests}?${params.toString()}`,
    );
  },

  answer: async (
    requestId: string,
    payload: UserInputAnswerRequest,
  ): Promise<UserInputRequest> => {
    return apiClient.post<UserInputRequest>(
      API_ENDPOINTS.userInputAnswer(requestId),
      payload,
    );
  },
};
