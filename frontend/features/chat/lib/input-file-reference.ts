import type {
  ChatFileReference,
  InputFile,
} from "@/features/chat/types/api/session";
import type { FileNode } from "@/features/chat/types/api/file";

export interface InputFileReferenceTrigger {
  start: number;
  end: number;
  query: string;
}

interface BaseInputFileReferenceCandidate {
  id: string;
  displayName: string;
  description: string | null;
}

export interface UploadedInputFileReferenceCandidate extends BaseInputFileReferenceCandidate {
  kind: "input_file";
  file: InputFile;
  displayName: string;
  source: string;
}

export interface WorkspaceInputFileReferenceCandidate extends BaseInputFileReferenceCandidate {
  kind: "workspace_file";
  file: FileNode;
  sessionId: string;
  path: string;
}

export type InputFileReferenceCandidate =
  | UploadedInputFileReferenceCandidate
  | WorkspaceInputFileReferenceCandidate;

export interface InsertInputFileReferenceResult {
  value: string;
  cursor: number;
  reference: ChatFileReference;
}

function normalizeSource(source: unknown): string {
  return typeof source === "string" ? source.trim() : "";
}

function normalizeDisplayName(file: InputFile): string {
  const name = (file.name || "").trim();
  if (name) return name;
  const source = normalizeSource(file.source);
  return source || "file";
}

function formatDescription(file: InputFile): string | null {
  const parts = [
    typeof file.content_type === "string" && file.content_type.trim()
      ? file.content_type.trim()
      : null,
    typeof file.size === "number" ? `${file.size} B` : null,
    typeof file.path === "string" && file.path.trim() ? file.path.trim() : null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function normalizeWorkspacePath(path: unknown): string {
  if (typeof path !== "string") return "";
  const normalized = path.replace(/\\/g, "/").trim();
  if (!normalized) return "";
  return `/${normalized.replace(/^\/+/, "")}`;
}

function flattenWorkspaceFiles(nodes: FileNode[]): FileNode[] {
  const files: FileNode[] = [];

  function visit(items: FileNode[]) {
    for (const item of items) {
      if (item.type === "file") {
        files.push(item);
        continue;
      }
      if (Array.isArray(item.children)) {
        visit(item.children);
      }
    }
  }

  visit(nodes);
  return files;
}

function formatWorkspaceDescription(file: FileNode): string | null {
  const size =
    typeof file.oss_meta?.size === "number" ? `${file.oss_meta.size} B` : null;
  const parts = [
    typeof file.mimeType === "string" && file.mimeType.trim()
      ? file.mimeType.trim()
      : null,
    size,
    normalizeWorkspacePath(file.path) || null,
  ].filter(Boolean);
  return parts.length > 0 ? parts.join(" · ") : null;
}

function matchesQuery(
  displayName: string,
  path: string,
  query: string,
): boolean {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;
  return (
    displayName.toLowerCase().includes(normalizedQuery) ||
    path.toLowerCase().includes(normalizedQuery)
  );
}

export function getInputFileReferenceTrigger(
  value: string,
  cursor: number,
): InputFileReferenceTrigger | null {
  const boundedCursor = Math.max(0, Math.min(cursor, value.length));
  const beforeCursor = value.slice(0, boundedCursor);
  const tokenStart = beforeCursor.search(/(?:^|\s)#([^\s#/]*)$/);
  if (tokenStart === -1) return null;

  const hashIndex = beforeCursor.indexOf("#", tokenStart);
  if (hashIndex === -1) return null;

  return {
    start: hashIndex,
    end: boundedCursor,
    query: beforeCursor.slice(hashIndex + 1),
  };
}

export function getInputFileReferenceCandidates(
  files: InputFile[],
  query: string,
  options?: {
    sessionId?: string | null;
    workspaceFiles?: FileNode[];
  },
): InputFileReferenceCandidate[] {
  const seenKeys = new Set<string>();
  const candidates: InputFileReferenceCandidate[] = [];

  for (const file of files) {
    const source = normalizeSource(file.source);
    const key = `input_file:${source}`;
    if (!source || seenKeys.has(key)) continue;

    const displayName = normalizeDisplayName(file);
    if (!matchesQuery(displayName, source, query)) {
      continue;
    }

    candidates.push({
      id: key,
      kind: "input_file",
      file,
      source,
      displayName,
      description: formatDescription(file),
    });
    seenKeys.add(key);
  }

  const sessionId = (options?.sessionId || "").trim();
  if (sessionId && options?.workspaceFiles?.length) {
    for (const file of flattenWorkspaceFiles(options.workspaceFiles)) {
      const path = normalizeWorkspacePath(file.path);
      const key = `workspace_file:${sessionId}:${path}`;
      if (!path || seenKeys.has(key)) continue;

      const displayName = (file.name || path.split("/").pop() || path).trim();
      if (!matchesQuery(displayName, path, query)) {
        continue;
      }

      candidates.push({
        id: key,
        kind: "workspace_file",
        file,
        sessionId,
        path,
        displayName,
        description: formatWorkspaceDescription(file),
      });
      seenKeys.add(key);
    }
  }

  return candidates;
}

export function insertInputFileReference(
  value: string,
  selectionStart: number,
  selectionEnd: number,
  candidate: InputFileReferenceCandidate,
): InsertInputFileReferenceResult | null {
  const trigger = getInputFileReferenceTrigger(value, selectionStart);
  if (!trigger) return null;

  const insertedText = `#${candidate.displayName}`;
  const replacement = `${insertedText} `;
  const start = trigger.start;
  const end = Math.max(trigger.end, selectionEnd);
  const nextValue = `${value.slice(0, start)}${replacement}${value.slice(end)}`;
  const rangeEnd = start + insertedText.length;
  const range = { start, end: rangeEnd };

  const reference: ChatFileReference =
    candidate.kind === "input_file"
      ? {
          id: `${candidate.source}:${start}:${rangeEnd}`,
          kind: "input_file",
          source: candidate.source,
          insertedText,
          displayName: candidate.displayName,
          range,
          metadata: {
            inputFileId: candidate.file.id ?? null,
            size: candidate.file.size ?? null,
            contentType: candidate.file.content_type ?? null,
            path: candidate.file.path ?? null,
          },
        }
      : {
          id: `${candidate.sessionId}:${candidate.path}:${start}:${rangeEnd}`,
          kind: "workspace_file",
          sessionId: candidate.sessionId,
          path: candidate.path,
          insertedText,
          displayName: candidate.displayName,
          range,
          metadata: {
            size:
              typeof candidate.file.oss_meta?.size === "number"
                ? candidate.file.oss_meta.size
                : null,
            contentType: candidate.file.mimeType ?? null,
            sourceKind: candidate.file.source_kind ?? null,
          },
        };

  return {
    value: nextValue,
    cursor: start + replacement.length,
    reference,
  };
}

export function filterInputFileReferences(
  references: ChatFileReference[] | undefined,
  value: string,
  files: InputFile[],
  options?: {
    sessionId?: string | null;
    workspaceFiles?: FileNode[];
  },
): ChatFileReference[] {
  if (!references || references.length === 0) return [];

  const availableSources = new Set(
    files.map((file) => normalizeSource(file.source)).filter(Boolean),
  );
  const availableWorkspacePaths = new Set(
    flattenWorkspaceFiles(options?.workspaceFiles ?? [])
      .map((file) => normalizeWorkspacePath(file.path))
      .filter(Boolean),
  );
  const sessionId = (options?.sessionId || "").trim();
  const shouldCheckWorkspacePaths = availableWorkspacePaths.size > 0;
  const nextReferences: ChatFileReference[] = [];

  for (const reference of references) {
    const insertedText = reference.insertedText.trim();
    if (!insertedText) continue;

    if (reference.kind === "input_file") {
      const source = normalizeSource(reference.source);
      if (!source || !availableSources.has(source)) continue;
    } else if (reference.kind === "workspace_file") {
      if (sessionId && reference.sessionId !== sessionId) continue;
      const path = normalizeWorkspacePath(reference.path);
      if (!path) continue;
      if (shouldCheckWorkspacePaths && !availableWorkspacePaths.has(path)) {
        continue;
      }
    }

    const start = value.indexOf(insertedText);
    if (start === -1) continue;

    nextReferences.push({
      ...reference,
      range: {
        start,
        end: start + insertedText.length,
      },
    });
  }

  return nextReferences;
}
