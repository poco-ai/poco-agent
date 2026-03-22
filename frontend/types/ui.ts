/**
 * Cross-feature UI types shared across multiple feature modules.
 *
 * Types that are only used within a single feature should live in
 * that feature's own `types/` directory instead.
 */

/** Static metadata describing an available LLM model. */
export interface ModelInfo {
  id: string;
  name: string;
  descriptionKey: string;
  icon: string;
  provider: "anthropic" | "google";
}

/** Aggregated usage statistics for a session or account. */
export interface UsageStats {
  credits: number;
  tokensUsed: number;
  duration: number;
  todayUsage: number;
  weekUsage: number;
  monthUsage: number;
}

/** Generic file attachment metadata. */
export interface Attachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url: string;
}
