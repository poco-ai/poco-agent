"use client";

import type { LucideIcon } from "lucide-react";
import {
  Bot,
  BookOpen,
  Braces,
  Code2,
  Database,
  GitBranch,
  Globe,
  Paintbrush2,
  Sparkles,
} from "lucide-react";

import type { PresetIcon } from "@/features/capabilities/presets/lib/preset-types";

export const PRESET_ICON_ORDER: PresetIcon[] = [
  "default",
  "code",
  "branch",
  "database",
  "globe",
  "paintbrush",
  "book",
  "chip",
  "robot",
];

export const PRESET_ICON_MAP: Record<PresetIcon, LucideIcon> = {
  default: Sparkles,
  code: Code2,
  branch: GitBranch,
  database: Database,
  globe: Globe,
  paintbrush: Paintbrush2,
  book: BookOpen,
  chip: Braces,
  robot: Bot,
};

export const PRESET_COLOR_OPTIONS = [
  "#f97316",
  "#ef4444",
  "#eab308",
  "#22c55e",
  "#14b8a6",
  "#0ea5e9",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
  "#6b7280",
] as const;

export function getPresetIcon(icon: PresetIcon): LucideIcon {
  return PRESET_ICON_MAP[icon] ?? Sparkles;
}
