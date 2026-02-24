import type { ModelInfo } from "@/types";

export const AVAILABLE_MODELS: ModelInfo[] = [
  {
    id: "claude-sonnet-4.5",
    name: "Claude Sonnet 4.5",
    descriptionKey: "models.claudeSonnet45.description",
    icon: "⚡",
    provider: "anthropic",
  },
  {
    id: "claude-opus-4.5",
    name: "Claude Opus 4.5",
    descriptionKey: "models.claudeOpus45.description",
    icon: "🚀",
    provider: "anthropic",
  },
  {
    id: "gpt-4-turbo",
    name: "GPT-4 Turbo",
    descriptionKey: "models.gpt4Turbo.description",
    icon: "🧠",
    provider: "openai",
  },
];
