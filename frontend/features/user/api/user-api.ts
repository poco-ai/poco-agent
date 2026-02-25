import type { UserProfile, UserCredits } from "@/features/user/types";

// Mock user profile - TODO: Replace with real API call
// Note: planName and credits values should be translated by the caller using i18n keys:
// - user.plan.free / user.plan.pro / user.plan.team
// - user.credits.unlimited
const DEFAULT_USER_PROFILE: UserProfile = {
  id: "default-user",
  email: "user@poco.com",
  avatar: "",
  plan: "free",
  planName: "user.plan.free", // Translation key, should be resolved by caller
};

const DEFAULT_USER_CREDITS: UserCredits = {
  total: "user.credits.unlimited", // Translation key, should be resolved by caller
  free: "user.credits.unlimited", // Translation key, should be resolved by caller
  dailyRefreshCurrent: 9999,
  dailyRefreshMax: 9999,
  refreshTime: "08:00",
};

export const userService = {
  getProfile: async (): Promise<UserProfile> => {
    // TODO: Replace with real API call
    return DEFAULT_USER_PROFILE;
  },

  getCredits: async (): Promise<UserCredits> => {
    // TODO: Replace with real API call
    return DEFAULT_USER_CREDITS;
  },
};
