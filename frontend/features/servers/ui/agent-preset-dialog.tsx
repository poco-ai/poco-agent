"use client";

import * as React from "react";
import { Bot } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import type { Preset } from "@/features/capabilities/presets/lib/preset-types";
import type { ServerAgentItem } from "@/features/servers/model/types";
import { useT } from "@/lib/i18n/client";

export interface AgentPresetCreateInput {
  presetId: number;
  displayName: string;
  handle: string;
  description: string;
}

function normalizeAgentDisplayName(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function buildUniqueAgentDisplayName(
  displayName: string,
  existingAgents: ServerAgentItem[],
): string {
  const baseName = displayName.trim() || "Agent";
  const existingNames = new Set(
    existingAgents.map((agent) => normalizeAgentDisplayName(agent.displayName)),
  );
  if (!existingNames.has(normalizeAgentDisplayName(baseName))) {
    return baseName;
  }

  let suffix = 2;
  while (
    existingNames.has(normalizeAgentDisplayName(`${baseName} ${suffix}`))
  ) {
    suffix += 1;
  }
  return `${baseName} ${suffix}`;
}

export function AgentPresetDialog({
  open,
  presets,
  existingAgents,
  isWorking,
  onOpenChange,
  onCreateAgent,
}: {
  open: boolean;
  presets: Preset[];
  existingAgents: ServerAgentItem[];
  isWorking: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateAgent: (input: AgentPresetCreateInput) => void;
}) {
  const { t } = useT("translation");
  const autoDisplayNameRef = React.useRef<string | null>(null);
  const [presetId, setPresetId] = React.useState("");
  const [displayName, setDisplayName] = React.useState("");
  const [handle, setHandle] = React.useState("");
  const [description, setDescription] = React.useState("");

  React.useEffect(() => {
    if (!open) {
      setPresetId("");
      setDisplayName("");
      setHandle("");
      setDescription("");
      autoDisplayNameRef.current = null;
    }
  }, [open]);

  React.useEffect(() => {
    const preset = presets.find((item) => String(item.preset_id) === presetId);
    if (!preset) {
      return;
    }
    const nextDisplayName = buildUniqueAgentDisplayName(
      preset.name,
      existingAgents,
    );
    setDisplayName((current) => {
      if (!current || current === autoDisplayNameRef.current) {
        autoDisplayNameRef.current = nextDisplayName;
        return nextDisplayName;
      }
      return current;
    });
    setDescription((current) => current || preset.description || "");
  }, [existingAgents, presetId, presets]);

  const hasDisplayNameConflict = React.useMemo(() => {
    const normalizedDisplayName = normalizeAgentDisplayName(displayName);
    if (!normalizedDisplayName) {
      return false;
    }
    return existingAgents.some(
      (agent) =>
        normalizeAgentDisplayName(agent.displayName) === normalizedDisplayName,
    );
  }, [displayName, existingAgents]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("conversationView.agentPreset.title")}</DialogTitle>
          <DialogDescription>
            {t("conversationView.agentPreset.description")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-foreground">
              {t("conversationView.agentPreset.preset")}
            </label>
            <Select value={presetId} onValueChange={setPresetId}>
              <SelectTrigger className="border-border bg-background">
                <SelectValue
                  placeholder={t("conversationView.agentPreset.selectPreset")}
                />
              </SelectTrigger>
              <SelectContent>
                {presets.map((preset) => (
                  <SelectItem
                    key={preset.preset_id}
                    value={String(preset.preset_id)}
                  >
                    {preset.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Input
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder={t("conversationView.agentPreset.displayName")}
              aria-invalid={hasDisplayNameConflict}
            />
            <Input
              value={handle}
              onChange={(event) => setHandle(event.target.value)}
              placeholder={t("conversationView.agentPreset.handle")}
            />
          </div>
          {hasDisplayNameConflict ? (
            <p className="text-xs text-destructive">
              {t("conversationView.agentPreset.displayNameConflict")}
            </p>
          ) : null}
          <Textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            rows={4}
            placeholder={t("conversationView.agentPreset.agentDescription")}
            className="rounded-md border-border bg-background text-sm shadow-none"
          />
        </div>
        <DialogFooter>
          <Button
            type="button"
            size="sm"
            onClick={() =>
              onCreateAgent({
                presetId: Number(presetId),
                displayName,
                handle,
                description,
              })
            }
            disabled={
              isWorking ||
              !presetId ||
              !displayName.trim() ||
              hasDisplayNameConflict
            }
          >
            <Bot className="size-4" />
            {t("conversationView.agentPreset.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
