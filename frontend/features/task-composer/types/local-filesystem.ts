import type {
  FilesystemMode,
  LocalMountAccessMode,
  LocalMountConfig,
} from "@/features/chat/types/api/session";

export type DeploymentMode = "local" | "cloud";

export interface LocalFilesystemSupport {
  deployment_mode: DeploymentMode;
  local_mount_available: boolean;
}

export interface LocalFilesystemDraft {
  filesystem_mode: FilesystemMode;
  local_mounts: LocalMountConfig[];
}

export interface LocalMountDraftRow {
  client_id: string;
  id?: string;
  name: string;
  host_path: string;
  access_mode: LocalMountAccessMode;
}
