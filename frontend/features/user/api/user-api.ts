import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";
import type { UserCredits, UserProfile } from "@/features/user/types";

interface CurrentUserApiResponse {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string;
}

const DEFAULT_USER_CREDITS: UserCredits = {
  total: "user.credits.unlimited",
  free: "user.credits.unlimited",
  dailyRefreshCurrent: 9999,
  dailyRefreshMax: 9999,
  refreshTime: "08:00",
};

function mapUserProfile(payload: CurrentUserApiResponse): UserProfile {
  return {
    id: payload.id,
    email: payload.email,
    displayName: payload.display_name,
    avatar: payload.avatar_url,
    plan: "free",
    planName: "user.plan.free",
  };
}

export const userService = {
  async getProfile(): Promise<UserProfile | null> {
    try {
      const profile = await apiClient.get<CurrentUserApiResponse>(
        API_ENDPOINTS.authMe,
      );
      return mapUserProfile(profile);
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        return null;
      }
      throw error;
    }
  },

  async getCredits(): Promise<UserCredits> {
    return DEFAULT_USER_CREDITS;
  },

  async logout(): Promise<void> {
    await apiClient.post(API_ENDPOINTS.authLogout);
  },
};
