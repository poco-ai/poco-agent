"use client";

import { useState } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

import { EnvVarsGrid } from "@/features/capabilities/env-vars/components/env-vars-grid";
import {
  AddEnvVarDialog,
  type EnvVarDialogMode,
} from "@/features/capabilities/env-vars/components/add-env-var-dialog";

import { useEnvVarsStore } from "@/features/capabilities/env-vars/hooks/use-env-vars-store";
import type { EnvVar } from "@/features/capabilities/env-vars/types";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { useT } from "@/lib/i18n/client";

const RUNTIME_RISK_ACK_STORAGE_KEY = "runtime_env_risk_ack_v1";

export function EnvVarsPageClient() {
  const { t } = useT("translation");
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState<EnvVarDialogMode>("create");
  const [dialogInitialKey, setDialogInitialKey] = useState<string | undefined>(
    undefined,
  );
  const [dialogInitialDesc, setDialogInitialDesc] = useState<
    string | null | undefined
  >(undefined);
  const [pendingRuntimeEnableEnvVar, setPendingRuntimeEnableEnvVar] =
    useState<EnvVar | null>(null);
  const [hasRuntimeRiskAck, setHasRuntimeRiskAck] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.localStorage.getItem(RUNTIME_RISK_ACK_STORAGE_KEY) === "true";
  });
  const envVarStore = useEnvVarsStore();

  const openCreateDialog = () => {
    setDialogMode("create");
    setDialogInitialKey(undefined);
    setDialogInitialDesc(undefined);
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
              onToggleRuntime={(envVar, checked) => {
                if (
                  checked &&
                  !envVar.expose_to_runtime &&
                  !hasRuntimeRiskAck
                ) {
                  setPendingRuntimeEnableEnvVar(envVar);
                  return;
                }
                void envVarStore
                  .setRuntimeExposure(envVar, checked)
                  .catch(() => {
                    // Error toast is handled upstream.
                  });
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
          </CapabilityContentShell>
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

      <AlertDialog
        open={pendingRuntimeEnableEnvVar !== null}
        onOpenChange={(open) => {
          if (!open) {
            setPendingRuntimeEnableEnvVar(null);
          }
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("library.envVars.runtimeRiskTitle")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t("library.envVars.runtimeRiskDescription")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={envVarStore.savingEnvKey !== null}>
              {t("common.cancel")}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                if (!pendingRuntimeEnableEnvVar) return;
                event.preventDefault();
                void envVarStore
                  .setRuntimeExposure(pendingRuntimeEnableEnvVar, true)
                  .then(() => {
                    if (typeof window !== "undefined") {
                      window.localStorage.setItem(
                        RUNTIME_RISK_ACK_STORAGE_KEY,
                        "true",
                      );
                    }
                    setHasRuntimeRiskAck(true);
                    setPendingRuntimeEnableEnvVar(null);
                  })
                  .catch(() => {
                    // Keep the dialog open so the user can retry after the toast.
                  });
              }}
              disabled={envVarStore.savingEnvKey !== null}
            >
              {t("library.envVars.runtimeRiskConfirm")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
