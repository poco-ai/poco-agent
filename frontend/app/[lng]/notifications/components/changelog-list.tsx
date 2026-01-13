"use client";

import * as React from "react";
import { CheckCircle2, GitCommit, Rocket, Zap } from "lucide-react";

interface ChangeLogItem {
  version: string;
  date: string;
  features: {
    title: string;
    description: string;
    type: "feature" | "improvement" | "fix";
  }[];
}

const MOCK_CHANGELOG: ChangeLogItem[] = [
  {
    version: "v1.2.0",
    date: "2024-03-20",
    features: [
      {
        title: "Skills Store",
        description:
          "New skills marketplace to browse and install AI capabilities.",
        type: "feature",
      },
      {
        title: "Task Drag & Drop",
        description:
          "Improved sidebar task management with drag and drop support.",
        type: "improvement",
      },
    ],
  },
  {
    version: "v1.1.0",
    date: "2024-03-10",
    features: [
      {
        title: "Dark Mode",
        description:
          "Full dark mode support for better visual experience at night.",
        type: "feature",
      },
      {
        title: "Performance Optimization",
        description: "Reduced Initial load time by 40%.",
        type: "improvement",
      },
      {
        title: "Login Bug Fix",
        description:
          "Fixed an issue where session was not persisting correctly.",
        type: "fix",
      },
    ],
  },
  {
    version: "v1.0.0",
    date: "2024-02-28",
    features: [
      {
        title: "Initial Release",
        description:
          "Launch of OpenCoWork with core project and task management features.",
        type: "feature",
      },
    ],
  },
];

export function ChangelogList() {
  return (
    <div className="space-y-12 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
      {MOCK_CHANGELOG.map((log) => (
        <div
          key={log.version}
          className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
        >
          {/* Icon */}
          <div className="flex items-center justify-center size-10 rounded-full border border-border bg-background shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
            <GitCommit className="size-5 text-primary" />
          </div>

          {/* Content Card */}
          <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] p-6 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-bold text-lg flex items-center gap-2">
                <span className="text-primary">{log.version}</span>
                <span className="text-muted-foreground text-sm font-normal">
                  released on {log.date}
                </span>
              </h3>
            </div>

            <div className="space-y-4">
              {log.features.map((feature, i) => (
                <div key={i} className="flex gap-3">
                  <div className="mt-1 shrink-0">
                    {feature.type === "feature" && (
                      <Rocket className="size-4 text-blue-500" />
                    )}
                    {feature.type === "improvement" && (
                      <Zap className="size-4 text-amber-500" />
                    )}
                    {feature.type === "fix" && (
                      <CheckCircle2 className="size-4 text-green-500" />
                    )}
                  </div>
                  <div>
                    <h4 className="font-medium text-sm text-foreground">
                      {feature.title}
                    </h4>
                    <p className="text-sm text-muted-foreground leading-relaxed mt-0.5">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
