import * as React from "react";

import {
  SubAgentDialog,
  type SubAgentDialogMode,
} from "@/features/capabilities/sub-agents/components/sub-agent-dialog";
import { SubAgentsList } from "@/features/capabilities/sub-agents/components/sub-agents-list";
import type {
  SubAgent,
  SubAgentCreateInput,
  SubAgentUpdateInput,
} from "@/features/capabilities/sub-agents/types";
import { useT } from "@/lib/i18n/client";

import { AdminSectionError, AdminSectionLoading } from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface AdminSubAgentsSectionProps {
  subAgents: SubAgent[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: SubAgentCreateInput) => Promise<void>;
  onUpdate: (subAgentId: number, input: SubAgentUpdateInput) => Promise<void>;
  onDelete: (subAgentId: number) => Promise<void>;
}

export function AdminSubAgentsSection({
  subAgents,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminSubAgentsSectionProps) {
  const { t } = useT("translation");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [dialogMode, setDialogMode] =
    React.useState<SubAgentDialogMode>("create");
  const [editing, setEditing] = React.useState<SubAgent | null>(null);
  const [searchQuery, setSearchQuery] = React.useState("");

  const filteredSubAgents = React.useMemo(() => {
    if (!searchQuery) return subAgents;
    const lowerQuery = searchQuery.toLowerCase();
    return subAgents.filter((agent) => {
      return (
        agent.name.toLowerCase().includes(lowerQuery) ||
        (agent.description || "").toLowerCase().includes(lowerQuery) ||
        (agent.prompt || "").toLowerCase().includes(lowerQuery) ||
        (agent.raw_markdown || "").toLowerCase().includes(lowerQuery)
      );
    });
  }, [searchQuery, subAgents]);

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.subAgentsTitle")}
        description={t("settings.admin.subAgentsDescription")}
        summary={`${t("settings.admin.subAgentsTitle")} · ${filteredSubAgents.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.subAgents.searchPlaceholder")}
        createLabel={t("library.subAgents.addCard")}
        onCreate={() => {
          setDialogMode("create");
          setEditing(null);
          setDialogOpen(true);
        }}
      >
        {isLoading ? <AdminSectionLoading /> : null}
        {hasError ? <AdminSectionError onRetry={onRetry} /> : null}
        <div
          className={
            isLoading || hasError ? "pointer-events-none opacity-60" : undefined
          }
        >
          <SubAgentsList
            subAgents={filteredSubAgents}
            savingId={isSaving ? (editing?.id ?? -1) : null}
            isLoading={isLoading}
            onToggleEnabled={(id, enabled) => void onUpdate(id, { enabled })}
            onEdit={(agent) => {
              setDialogMode("edit");
              setEditing(agent);
              setDialogOpen(true);
            }}
            onDelete={(agent) => void onDelete(agent.id)}
          />
        </div>
      </AdminCatalogShell>

      <SubAgentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        initialAgent={editing}
        isSaving={isSaving}
        onCreate={async (input) => {
          await onCreate(input);
          return null;
        }}
        onUpdate={async (subAgentId, input) => {
          await onUpdate(subAgentId, input);
          return null;
        }}
      />
    </>
  );
}
