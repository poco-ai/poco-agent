"use client";

import { Loader2 } from "lucide-react";
import { CapabilityContentShell } from "@/features/capabilities/components/capability-content-shell";
import { usePermissionPolicy } from "../hooks/use-permission-policy";
import { PermissionPolicyEditor } from "./permission-policy-editor";

export function PermissionsPageClient() {
  const { policy, isLoading, isSaving, setPolicy, save } =
    usePermissionPolicy();

  if (isLoading) {
    return (
      <div className="flex min-h-[200px] items-center justify-center text-sm text-muted-foreground">
        <Loader2 className="mr-2 size-4 animate-spin" />
      </div>
    );
  }

  return (
    <CapabilityContentShell>
      <PermissionPolicyEditor
        policy={policy}
        isSaving={isSaving}
        onChange={setPolicy}
        onSave={save}
      />
    </CapabilityContentShell>
  );
}
