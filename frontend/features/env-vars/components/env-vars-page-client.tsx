"use client";

import { useState } from "react";

import { EnvVarsHeader } from "@/features/env-vars/components/env-vars-header";
import { EnvVarsGrid } from "@/features/env-vars/components/env-vars-grid";
import {
  AddEnvVarDialog,
  type EnvVarDialogMode,
} from "@/features/env-vars/components/add-env-var-dialog";

import { useEnvVarsStore } from "@/features/env-vars/hooks/use-env-vars-store";
import type { EnvVar } from "@/features/env-vars/types";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";

export function EnvVarsPageClient() {
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<EnvVarDialogMode>("create");
  const [dialogInitialKey, setDialogInitialKey] = useState<string | undefined>(
    undefined,
  );
  const [dialogInitialDesc, setDialogInitialDesc] = useState<
    string | null | undefined
  >(undefined);
  const envVarStore = useEnvVarsStore();

  return (
    <>
      <EnvVarsHeader
        onAddClick={() => {
          setDialogMode("create");
          setDialogInitialKey(undefined);
          setDialogInitialDesc(undefined);
          setIsAddDialogOpen(true);
        }}
      />

      <div className="flex flex-1 flex-col overflow-hidden">
        <PullToRefresh
          onRefresh={envVarStore.refreshEnvVars}
          isLoading={envVarStore.isLoading}
        >
          <div className="flex flex-1 flex-col px-6 py-6 overflow-auto">
            <div className="w-full max-w-6xl mx-auto">
              <EnvVarsGrid
                envVars={envVarStore.envVars}
                savingKey={envVarStore.savingEnvKey}
                onDelete={(id) => {
                  envVarStore.removeEnvVar(id);
                }}
                onEdit={(envVar: EnvVar) => {
                  setDialogMode("edit");
                  setDialogInitialKey(envVar.key);
                  setDialogInitialDesc(envVar.description);
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
                    setIsAddDialogOpen(true);
                    return;
                  }
                  setDialogMode("override");
                  setDialogInitialKey(key);
                  setDialogInitialDesc(undefined);
                  setIsAddDialogOpen(true);
                }}
              />
            </div>
          </div>
        </PullToRefresh>
      </div>

      <AddEnvVarDialog
        open={isAddDialogOpen}
        onOpenChange={setIsAddDialogOpen}
        mode={dialogMode}
        initialKey={dialogInitialKey}
        initialDescription={dialogInitialDesc}
        onSave={async (payload) => {
          await envVarStore.upsertEnvVar(payload);
        }}
        isSaving={envVarStore.savingEnvKey !== null}
      />
    </>
  );
}
