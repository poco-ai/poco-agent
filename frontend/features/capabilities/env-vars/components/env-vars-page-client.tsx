"use client";

import { useState } from "react";

import { EnvVarsGrid } from "@/features/capabilities/env-vars/components/env-vars-grid";
import {
  AddEnvVarDialog,
  type EnvVarDialogMode,
} from "@/features/capabilities/env-vars/components/add-env-var-dialog";

import { useEnvVarsStore } from "@/features/capabilities/env-vars/hooks/use-env-vars-store";
import type { EnvVar } from "@/features/capabilities/env-vars/types";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";

export function EnvVarsPageClient() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<EnvVarDialogMode>("create");
  const [dialogInitialKey, setDialogInitialKey] = useState<string | undefined>(
    undefined,
  );
  const [dialogInitialDesc, setDialogInitialDesc] = useState<
    string | null | undefined
  >(undefined);
  const [dialogInitialExposeToRuntime, setDialogInitialExposeToRuntime] =
    useState<boolean | undefined>(undefined);
  const envVarStore = useEnvVarsStore();

  const openCreateDialog = () => {
    setDialogMode("create");
    setDialogInitialKey(undefined);
    setDialogInitialDesc(undefined);
    setDialogInitialExposeToRuntime(false);
    setIsAddDialogOpen(true);
  };

  return (
    <>
      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh
          onRefresh={envVarStore.refreshEnvVars}
          isLoading={envVarStore.isLoading}
        >
          <CapabilityContentShell>
            <EnvVarsGrid
              envVars={envVarStore.envVars}
              savingKey={envVarStore.savingEnvKey}
              isLoading={envVarStore.isLoading}
              onAddClick={openCreateDialog}
              onDelete={(id) => {
                envVarStore.removeEnvVar(id);
              }}
              onEdit={(envVar: EnvVar) => {
                setDialogMode("edit");
                setDialogInitialKey(envVar.key);
                setDialogInitialDesc(envVar.description);
                setDialogInitialExposeToRuntime(envVar.expose_to_runtime);
                setIsAddDialogOpen(true);
              }}
              onOverrideSystem={(key: string) => {
                const existingUser = envVarStore.envVars.find(
                  (v) => v.scope === "user" && v.key === key,
                );
                if (existingUser) {
                  setDialogMode("edit");
                  setDialogInitialKey(existingUser.key);
                  setDialogInitialDesc(existingUser.description);
                  setDialogInitialExposeToRuntime(
                    existingUser.expose_to_runtime,
                  );
                  setIsAddDialogOpen(true);
                  return;
                }
                setDialogMode("override");
                setDialogInitialKey(key);
                setDialogInitialDesc(undefined);
                setDialogInitialExposeToRuntime(false);
                setIsAddDialogOpen(true);
              }}
            />
          </CapabilityContentShell>
        </PullToRefresh>
      </div>

      <AddEnvVarDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        mode={dialogMode}
        initialKey={dialogInitialKey}
        initialDescription={dialogInitialDesc}
        initialExposeToRuntime={dialogInitialExposeToRuntime}
        onSave={async (payload) => {
          await envVarStore.upsertEnvVar(payload);
        }}
        isSaving={envVarStore.savingEnvKey !== null}
      />
    </>
  );
}
