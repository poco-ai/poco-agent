"use client";

import { useState } from "react";

import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { SubAgentsHeader } from "@/features/sub-agents/components/sub-agents-header";
import { SubAgentsList } from "@/features/sub-agents/components/sub-agents-list";
import {
  SubAgentDialog,
  type SubAgentDialogMode,
} from "@/features/sub-agents/components/sub-agent-dialog";
import { useSubAgentsStore } from "@/features/sub-agents/hooks/use-sub-agents-store";
import type { SubAgent } from "@/features/sub-agents/types";

export function SubAgentsPageClient() {
  const store = useSubAgentsStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<SubAgentDialogMode>("create");
  const [editing, setEditing] = useState<SubAgent | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = store.subAgents.filter((agent) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      agent.name.toLowerCase().includes(q) ||
      (agent.description || "").toLowerCase().includes(q) ||
      (agent.prompt || "").toLowerCase().includes(q) ||
      (agent.raw_markdown || "").toLowerCase().includes(q)
    );
  });

  return (
    <>
      <SubAgentsHeader
        onAddClick={() => {
          setDialogMode("create");
          setEditing(null);
          setDialogOpen(true);
        }}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh onRefresh={store.refresh} isLoading={store.isLoading}>
          <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
            <div className="w-full max-w-4xl mx-auto">
              <SubAgentsList
                subAgents={filtered}
                savingId={store.savingId}
                isLoading={store.isLoading}
                onToggleEnabled={(id, enabled) => store.setEnabled(id, enabled)}
                onEdit={(agent) => {
                  setDialogMode("edit");
                  setEditing(agent);
                  setDialogOpen(true);
                }}
                onDelete={(agent) => store.deleteSubAgent(agent.id)}
              />
            </div>
          </div>
        </PullToRefresh>
      </div>

      <SubAgentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        initialAgent={editing}
        isSaving={store.savingId !== null}
        onCreate={store.createSubAgent}
        onUpdate={store.updateSubAgent}
      />
    </>
  );
}
