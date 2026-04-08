export interface UserProfile {
  id: string;
  email: string | null;
  displayName?: string | null;
  avatar?: string | null;
  plan: "free" | "pro" | "team";
  planName: string;
}

export interface UserCredits {
  total: number | string;
  free: number | string;
  dailyRefreshCurrent: number;
  dailyRefreshMax: number;
  refreshTime: string;
}
