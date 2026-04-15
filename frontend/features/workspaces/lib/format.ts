import type { TFunction } from "i18next";
import type { WorkspaceRole } from "@/features/workspaces/model/types";

export function formatWorkspaceRole(
  t: TFunction,
  role: WorkspaceRole,
): string {
  return t(`workspaces.roles.${role}`);
}

export function formatWorkspaceKind(t: TFunction, kind: string): string {
  return t(`workspaces.kinds.${kind}`, kind);
}

export function formatActivityAction(t: TFunction, action: string): string {
  return t(`workspaces.activity.actions.${action}`, action);
}
