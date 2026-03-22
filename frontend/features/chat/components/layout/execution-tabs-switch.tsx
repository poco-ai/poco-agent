"use client";

import { Layers, Monitor } from "lucide-react";
import { motion } from "motion/react";
import { TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import { useT } from "@/lib/i18n/client";

interface ExecutionTabsSwitchProps {
  rightTab: string;
  highlightId: string;
  showArtifactsTab: boolean;
  showComputerTab: boolean;
}

export function ExecutionTabsSwitch({
  rightTab,
  highlightId,
  showArtifactsTab,
  showComputerTab,
}: ExecutionTabsSwitchProps) {
  const { t } = useT("translation");

  return (
    <TabsList className="min-w-0 max-w-full overflow-hidden font-serif">
      {showComputerTab ? (
        <TabsTrigger
          value="computer"
          asChild
          className="!flex-none min-w-0 border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-transparent"
        >
          <button
            type="button"
            className={cn(
              "relative inline-flex h-[calc(100%-1px)] flex-1 min-w-0 items-center justify-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-1",
              rightTab === "computer"
                ? "text-primary-foreground"
                : "text-muted-foreground",
            )}
          >
            {rightTab === "computer" ? (
              <motion.div
                layoutId={`execution-tabs-${highlightId}`}
                className="absolute inset-0 rounded-md bg-primary shadow-sm"
                transition={{ type: "spring", stiffness: 440, damping: 40 }}
              />
            ) : null}
            <Monitor className="relative z-10 size-4 shrink-0" />
            <span className="relative z-10 truncate">
              {t("mobile.computer")}
            </span>
          </button>
        </TabsTrigger>
      ) : null}
      {showArtifactsTab ? (
        <TabsTrigger
          value="artifacts"
          asChild
          className="!flex-none min-w-0 border-transparent data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:border-transparent"
        >
          <button
            type="button"
            className={cn(
              "relative inline-flex h-[calc(100%-1px)] flex-1 min-w-0 items-center justify-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:ring-offset-1",
              rightTab === "artifacts"
                ? "text-primary-foreground"
                : "text-muted-foreground",
            )}
          >
            {rightTab === "artifacts" ? (
              <motion.div
                layoutId={`execution-tabs-${highlightId}`}
                className="absolute inset-0 rounded-md bg-primary shadow-sm"
                transition={{ type: "spring", stiffness: 440, damping: 40 }}
              />
            ) : null}
            <Layers className="relative z-10 size-4 shrink-0" />
            <span className="relative z-10 truncate">
              {t("mobile.artifacts")}
            </span>
          </button>
        </TabsTrigger>
      ) : null}
    </TabsList>
  );
}
