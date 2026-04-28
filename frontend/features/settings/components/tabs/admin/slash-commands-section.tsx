import * as React from "react";

import {
  SlashCommandDialog,
  type SlashCommandDialogMode,
} from "@/features/capabilities/slash-commands/components/slash-command-dialog";
import { SlashCommandsList } from "@/features/capabilities/slash-commands/components/slash-commands-list";
import type {
  SlashCommand,
  SlashCommandCreateInput,
  SlashCommandUpdateInput,
} from "@/features/capabilities/slash-commands/types";
import { useT } from "@/lib/i18n/client";

import { AdminSectionError, AdminSectionLoading } from "./shared";
import { AdminCatalogShell } from "./admin-catalog-shell";

interface AdminSlashCommandsSectionProps {
  commands: SlashCommand[];
  isLoading: boolean;
  hasError: boolean;
  isSaving: boolean;
  onRetry: () => void;
  onCreate: (input: SlashCommandCreateInput) => Promise<void>;
  onUpdate: (
    commandId: number,
    input: SlashCommandUpdateInput,
  ) => Promise<void>;
  onDelete: (commandId: number) => Promise<void>;
}

export function AdminSlashCommandsSection({
  commands,
  isLoading,
  hasError,
  isSaving,
  onRetry,
  onCreate,
  onUpdate,
  onDelete,
}: AdminSlashCommandsSectionProps) {
  const { t } = useT("translation");
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [dialogMode, setDialogMode] =
    React.useState<SlashCommandDialogMode>("create");
  const [editing, setEditing] = React.useState<SlashCommand | null>(null);
  const [searchQuery, setSearchQuery] = React.useState("");

  const filteredCommands = React.useMemo(() => {
    if (!searchQuery) return commands;
    const lowerQuery = searchQuery.toLowerCase();
    return commands.filter((cmd) => {
      return (
        cmd.name.toLowerCase().includes(lowerQuery) ||
        (cmd.description || "").toLowerCase().includes(lowerQuery) ||
        (cmd.content || "").toLowerCase().includes(lowerQuery) ||
        (cmd.raw_markdown || "").toLowerCase().includes(lowerQuery)
      );
    });
  }, [commands, searchQuery]);

  return (
    <>
      <AdminCatalogShell
        title={t("settings.admin.slashCommandsTitle")}
        description={t("settings.admin.slashCommandsDescription")}
        summary={`${t("settings.admin.slashCommandsTitle")} · ${filteredCommands.length}`}
        searchValue={searchQuery}
        onSearchChange={setSearchQuery}
        searchPlaceholder={t("library.slashCommands.searchPlaceholder")}
        createLabel={t("library.slashCommands.addCard")}
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
          <SlashCommandsList
            commands={filteredCommands}
            savingId={isSaving ? (editing?.id ?? -1) : null}
            isLoading={isLoading}
            onToggleEnabled={(id, enabled) => void onUpdate(id, { enabled })}
            onEdit={(cmd) => {
              setDialogMode("edit");
              setEditing(cmd);
              setDialogOpen(true);
            }}
            onDelete={(cmd) => void onDelete(cmd.id)}
          />
        </div>
      </AdminCatalogShell>

      <SlashCommandDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        mode={dialogMode}
        initialCommand={editing}
        isSaving={isSaving}
        onCreate={async (input) => {
          await onCreate(input);
          return null;
        }}
        onUpdate={async (commandId, input) => {
          await onUpdate(commandId, input);
          return null;
        }}
      />
    </>
  );
}
