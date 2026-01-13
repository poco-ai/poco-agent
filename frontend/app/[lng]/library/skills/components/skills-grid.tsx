"use client";

import * as React from "react";
import { Layers, Terminal, Globe, Code2, PenTool } from "lucide-react";
import { cn } from "@/lib/utils";
import { useT } from "@/app/i18n/client";

interface Skill {
  id: string;
  nameKey: string;
  descKey: string;
  source: string;
  icon?: React.ReactNode;
}

const SKILL_ITEMS: Omit<Skill, "name" | "description">[] = [
  {
    id: "1",
    nameKey: "library.skillsPage.items.webSearch.name",
    descKey: "library.skillsPage.items.webSearch.description",
    source: "Google Search API",
    icon: <Globe className="size-5" />,
  },
  {
    id: "2",
    nameKey: "library.skillsPage.items.codeExecution.name",
    descKey: "library.skillsPage.items.codeExecution.description",
    source: "Python Sandbox",
    icon: <Terminal className="size-5" />,
  },
  {
    id: "3",
    nameKey: "library.skillsPage.items.imageGeneration.name",
    descKey: "library.skillsPage.items.imageGeneration.description",
    source: "DALL-E 3",
    icon: <Layers className="size-5" />,
  },
  {
    id: "4",
    nameKey: "library.skillsPage.items.textAnalysis.name",
    descKey: "library.skillsPage.items.textAnalysis.description",
    source: "Natural Language API",
    icon: <PenTool className="size-5" />,
  },
  {
    id: "5",
    nameKey: "library.skillsPage.items.dataVisualization.name",
    descKey: "library.skillsPage.items.dataVisualization.description",
    source: "Matplotlib",
    icon: <Code2 className="size-5" />,
  },
];

export function SkillsGrid() {
  const { t } = useT("translation");

  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      {SKILL_ITEMS.map((skill) => (
        <div
          key={skill.id}
          className={cn(
            "group relative flex flex-col overflow-hidden rounded-xl bg-card border border-border/50",
            "transition-all duration-300 hover:shadow-lg hover:-translate-y-0.5 hover:border-primary/20",
          )}
        >
          <div className="p-5 flex flex-col h-full">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="flex items-center justify-center p-2 rounded-lg bg-primary/5 text-primary group-hover:bg-primary/10 transition-colors">
                  {skill.icon || <Terminal className="size-5" />}
                </div>
                <div>
                  <h3 className="font-semibold tracking-tight text-foreground">
                    {t(skill.nameKey)}
                  </h3>
                  <div className="text-xs text-muted-foreground mt-0.5 flex items-center gap-1">
                    <span className="inline-block size-1.5 rounded-full bg-primary/40"></span>
                    {skill.source}
                  </div>
                </div>
              </div>
            </div>

            <p className="text-sm text-muted-foreground leading-relaxed line-clamp-3">
              {t(skill.descKey)}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
