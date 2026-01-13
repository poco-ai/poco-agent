import { useState, useEffect } from "react";

export interface UserProfile {
  id: string;
  email: string;
  avatar?: string;
  plan: "free" | "pro" | "team";
  planName: string; // Display name e.g. "免费版"
}

export interface UserCredits {
  total: number | string;
  free: number | string;
  dailyRefreshCurrent: number;
  dailyRefreshMax: number;
  refreshTime: string; // e.g. "08:00"
}

// Mock Data Definitions
const MOCK_PROFILE: UserProfile = {
  id: "u_123456",
  email: "user@opencowork.com",
  avatar: "",
  plan: "free",
  planName: "免费",
};

const MOCK_CREDITS: UserCredits = {
  total: "∞",
  free: "∞",
  dailyRefreshCurrent: 9999,
  dailyRefreshMax: 9999,
  refreshTime: "08:00",
};

export function useUserAccount() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [credits, setCredits] = useState<UserCredits | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Simulate API fetch delay
    const fetchUserData = async () => {
      try {
        // TODO: Replace with actual API calls
        // const profileRes = await fetch('/api/user/profile');
        // const creditsRes = await fetch('/api/user/credits');

        await new Promise((resolve) => setTimeout(resolve, 500)); // Mock delay

        setProfile(MOCK_PROFILE);
        setCredits(MOCK_CREDITS);
      } catch (error) {
        console.error("Failed to fetch user data", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUserData();
  }, []);

  return {
    profile,
    credits,
    isLoading,
  };
}
