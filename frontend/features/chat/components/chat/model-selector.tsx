"use client";

import * as React from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { AVAILABLE_MODELS } from "@/features/chat/constants/models";
import type { ModelInfo } from "@/types";
import { useT } from "@/lib/i18n/client";

interface ModelSelectorProps {
  model: ModelInfo;
  onChange: (model: ModelInfo) => void;
}

export function ModelSelector({ model, onChange }: ModelSelectorProps) {
  const { t } = useT("translation");
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2">
          <span className="text-base">{model.icon}</span>
          <span className="font-medium font-serif">{model.name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        {AVAILABLE_MODELS.map((m) => (
          <DropdownMenuItem
            key={m.id}
            onClick={() => onChange(m)}
            className="flex items-start gap-3 p-3"
          >
            <span className="text-xl mt-0.5">{m.icon}</span>
            <div className="flex-1">
              <div className="font-medium">{m.name}</div>
              <div className="text-xs text-muted-foreground">
                {t(m.descriptionKey)}
              </div>
            </div>
            {m.id === model.id && <div className="text-primary text-sm">✓</div>}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
