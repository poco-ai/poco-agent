"use client";

import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CapabilityCard } from "./capability-card";
import type { CapabilityItem } from "./capability-item-list";

const gridStyles = cn(
  "flex flex-nowrap gap-4 overflow-x-auto",
  "[-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden",
  "md:grid md:grid-cols-3 md:overflow-visible",
);

export interface CapabilityCardConfig {
  icon: LucideIcon;
  title: string;
  items: CapabilityItem[];
  emptyText: string;
  onToggle: (toggleId: number, enabled: boolean) => void;
  onNavigate: () => void;
  showWarning?: boolean;
  onWarningClick?: () => void;
}

export interface ConnectToolsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  cards: CapabilityCardConfig[];
  isLoading: boolean;
  hasFetched: boolean;
}

export function ConnectToolsDialog({
  open,
  onOpenChange,
  title,
  cards,
  isLoading,
  hasFetched,
}: ConnectToolsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="w-[1700px] max-w-[1400px] border-border bg-background p-0 text-foreground"
        aria-describedby="connect-tools-description"
        ariaTitle={title}
      >
        <DialogHeader className="border-b border-border px-6 py-4">
          <DialogTitle id="connect-tools-title">{title}</DialogTitle>
        </DialogHeader>
        <main
          id="connect-tools-description"
          className="px-4 pb-4 pt-0 md:px-6 md:pb-6"
          aria-label="Capability categories"
        >
          <section className={gridStyles} aria-label="MCP, Skills, and Presets">
            {cards.map((card) => (
              <CapabilityCard
                key={card.title}
                icon={card.icon}
                title={card.title}
                items={card.items}
                emptyText={card.emptyText}
                isLoading={isLoading}
                hasFetched={hasFetched}
                onToggle={card.onToggle}
                onNavigate={card.onNavigate}
                showWarning={card.showWarning}
                onWarningClick={card.onWarningClick}
              />
            ))}
          </section>
        </main>
      </DialogContent>
    </Dialog>
  );
}
