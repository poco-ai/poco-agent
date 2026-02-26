import type { LucideIcon } from "lucide-react";
import {
  Code,
  Globe,
  MoreHorizontal,
  Palette,
  Presentation,
} from "lucide-react";

export type QuickAction = {
  id: string;
  labelKey: string;
  icon: LucideIcon;
};

export const QUICK_ACTIONS: QuickAction[] = [
  { id: "slides", labelKey: "prompts.createSlides", icon: Presentation },
  { id: "website", labelKey: "prompts.createWebsite", icon: Globe },
  { id: "app", labelKey: "prompts.developApp", icon: Code },
  { id: "design", labelKey: "prompts.design", icon: Palette },
  { id: "more", labelKey: "prompts.more", icon: MoreHorizontal },
];
