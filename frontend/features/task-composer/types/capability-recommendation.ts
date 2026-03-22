export type CapabilityRecommendationType = "mcp" | "skill";

export interface CapabilityRecommendation {
  type: CapabilityRecommendationType;
  id: number;
  name: string;
  description: string | null;
  score: number;
  default_enabled: boolean;
}

export interface CapabilityRecommendationsResponse {
  query: string;
  items: CapabilityRecommendation[];
}
