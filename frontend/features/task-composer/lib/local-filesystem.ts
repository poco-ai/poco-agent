import type { LocalMountConfig } from "@/features/chat/types/api/session";
import type {
  LocalFilesystemDraft,
  LocalFilesystemSupport,
  LocalMountDraftRow,
} from "@/features/task-composer/types/local-filesystem";

export interface LocalFilesystemValidationError {
  key: string;
  values?: Record<string, unknown>;
}

export interface LocalFilesystemValidationResult {
  ok: boolean;
  value?: LocalFilesystemDraft;
  error?: LocalFilesystemValidationError;
}

function createClientId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `mount-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createEmptyLocalMountDraftRow(
  overrides?: Partial<Pick<LocalMountDraftRow, "name" | "host_path">>,
): LocalMountDraftRow {
  return {
    client_id: createClientId(),
    name: overrides?.name ?? "",
    host_path: overrides?.host_path ?? "",
    access_mode: "ro",
  };
}

export function toLocalMountDraftRows(
  mounts: LocalMountConfig[] | null | undefined,
): LocalMountDraftRow[] {
  if (!mounts?.length) {
    return [createEmptyLocalMountDraftRow()];
  }

  return mounts.map((mount) => ({
    client_id: createClientId(),
    id: mount.id,
    name: mount.name,
    host_path: mount.host_path,
    access_mode: mount.access_mode ?? "ro",
  }));
}

function slugifyMountId(value: string): string {
  const slug = value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return slug || "mount";
}

function inferMountId(row: LocalMountDraftRow, fallbackIndex: number): string {
  const fromName = row.name.trim();
  if (row.id?.trim()) {
    return slugifyMountId(row.id);
  }
  if (fromName) {
    return slugifyMountId(fromName);
  }

  const segments = row.host_path.trim().split(/[\\/]/).filter(Boolean);
  const lastSegment = segments.at(-1);
  if (lastSegment) {
    return slugifyMountId(lastSegment);
  }

  return `mount-${fallbackIndex + 1}`;
}

function ensureUniqueMountId(id: string, usedIds: Set<string>): string {
  let candidate = id;
  let suffix = 2;
  while (usedIds.has(candidate)) {
    candidate = `${id}-${suffix}`;
    suffix += 1;
  }
  usedIds.add(candidate);
  return candidate;
}

export function validateLocalFilesystemDraft(
  filesystemMode: LocalFilesystemDraft["filesystem_mode"],
  rows: LocalMountDraftRow[],
  support: LocalFilesystemSupport | null,
): LocalFilesystemValidationResult {
  if (filesystemMode === "sandbox") {
    return {
      ok: true,
      value: {
        filesystem_mode: "sandbox",
        local_mounts: [],
      },
    };
  }

  if (support && !support.local_mount_available) {
    return {
      ok: false,
      error: { key: "validation.localMountUnavailable" },
    };
  }

  const normalizedRows = rows
    .map((row) => ({
      ...row,
      name: row.name.trim(),
      host_path: row.host_path.trim(),
    }))
    .filter((row) => row.name || row.host_path);

  if (normalizedRows.length === 0) {
    return {
      ok: false,
      error: { key: "validation.localMountCountRequired" },
    };
  }

  const seenPaths = new Set<string>();
  const usedIds = new Set<string>();
  const mounts: LocalMountConfig[] = [];

  for (const [index, row] of normalizedRows.entries()) {
    if (!row.name) {
      return {
        ok: false,
        error: { key: "validation.localMountNameRequired" },
      };
    }

    if (!row.host_path) {
      return {
        ok: false,
        error: { key: "validation.localMountPathRequired" },
      };
    }

    const normalizedPathKey = row.host_path.toLowerCase();
    if (seenPaths.has(normalizedPathKey)) {
      return {
        ok: false,
        error: {
          key: "validation.localMountPathDuplicate",
          values: { path: row.host_path },
        },
      };
    }
    seenPaths.add(normalizedPathKey);

    const baseId = inferMountId(row, index);
    const mountId = ensureUniqueMountId(baseId, usedIds);
    mounts.push({
      id: mountId,
      name: row.name,
      host_path: row.host_path,
      access_mode: row.access_mode,
    });
  }

  return {
    ok: true,
    value: {
      filesystem_mode: "local_mount",
      local_mounts: mounts,
    },
  };
}
