"use client";

import * as React from "react";
import { ArrowRight } from "lucide-react";

import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

export interface HomeBottomCardItem {
  id: string;
  title: string;
  description: string;
  onClick: () => void;
}

interface HomeBottomCardDeckProps {
  cards: HomeBottomCardItem[];
  className?: string;
}

export function HomeBottomCardDeck({
  cards,
  className,
}: HomeBottomCardDeckProps) {
  const { t } = useT("translation");
  const [activeIndex, setActiveIndex] = React.useState(0);

  React.useEffect(() => {
    if (cards.length === 0) return;
    setActiveIndex((prev) => Math.min(prev, cards.length - 1));
  }, [cards.length]);

  if (cards.length === 0) return null;

  const activeCard = cards[activeIndex];

  return (
    <div className={cn("flex w-full flex-col items-center", className)}>
      <button
        type="button"
        className={cn(
          "group relative w-full max-w-xl overflow-hidden rounded-3xl border border-border/60 bg-card/90 px-6 py-6 text-left shadow-sm",
          "transition-all hover:-translate-y-0.5 hover:border-foreground/20 hover:bg-accent/30 hover:shadow-md",
        )}
        onClick={activeCard.onClick}
      >
        <div className="pr-20 sm:pr-28">
          <h3 className="text-lg font-semibold tracking-tight text-foreground">
            {activeCard.title}
          </h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {activeCard.description}
          </p>
        </div>

        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 right-0 hidden w-32 flex-col justify-center gap-4 pr-4 sm:flex"
        >
          {["bg-primary/80", "bg-muted-foreground/65", "bg-foreground/40"].map(
            (colorClass) => (
              <div
                key={colorClass}
                className="flex items-center gap-2 rounded-xl border border-border/60 bg-card/70 px-2 py-2"
              >
                <span
                  className={cn("size-5 shrink-0 rounded-md", colorClass)}
                />
                <div className="flex-1 space-y-1">
                  <div className="h-1.5 w-9 rounded bg-muted-foreground/25" />
                  <div className="h-1.5 w-11 rounded bg-muted-foreground/15" />
                </div>
              </div>
            ),
          )}
        </div>

        <ArrowRight className="absolute bottom-5 right-5 size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
      </button>

      <div className="mt-4 flex items-center gap-2">
        {cards.map((card, index) => {
          const isActive = index === activeIndex;
          return (
            <button
              key={card.id}
              type="button"
              aria-label={t("hero.bottomCards.selectCard", {
                index: index + 1,
              })}
              className={cn(
                "size-2.5 rounded-full transition-colors",
                isActive
                  ? "bg-muted-foreground/60"
                  : "bg-muted-foreground/20 hover:bg-muted-foreground/35",
              )}
              onClick={() => setActiveIndex(index)}
            />
          );
        })}
      </div>
    </div>
  );
}
