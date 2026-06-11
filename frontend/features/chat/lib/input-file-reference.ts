import type {
  ChatInputFileReference,
  InputFile,
} from "@/features/chat/types/api/session";

export interface InputFileReferenceTrigger {
  start: number;
  end: number;
  query: string;
}

export interface InputFileReferenceCandidate {
  file: InputFile;
  source: string;
  displayName: string;
  description: string | null;
}

export interface InsertInputFileReferenceResult {
  value: string;
  cursor: number;
  reference: ChatInputFileReference;
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
): InputFileReferenceCandidate[] {
  const normalizedQuery = query.trim().toLowerCase();
  const seenSources = new Set<string>();
  const candidates: InputFileReferenceCandidate[] = [];

  for (const file of files) {
    const source = normalizeSource(file.source);
    if (!source || seenSources.has(source)) continue;

    const displayName = normalizeDisplayName(file);
    if (
      normalizedQuery &&
      !displayName.toLowerCase().includes(normalizedQuery)
    ) {
      continue;
    }

    candidates.push({
      file,
      source,
      displayName,
      description: formatDescription(file),
    });
    seenSources.add(source);
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

  return {
    value: nextValue,
    cursor: start + replacement.length,
    reference: {
      id: `${candidate.source}:${start}:${rangeEnd}`,
      kind: "input_file",
      source: candidate.source,
      insertedText,
      displayName: candidate.displayName,
      range: { start, end: rangeEnd },
      metadata: {
        inputFileId: candidate.file.id ?? null,
        size: candidate.file.size ?? null,
        contentType: candidate.file.content_type ?? null,
        path: candidate.file.path ?? null,
      },
    },
  };
}

export function filterInputFileReferences(
  references: ChatInputFileReference[] | undefined,
  value: string,
  files: InputFile[],
): ChatInputFileReference[] {
  if (!references || references.length === 0) return [];

  const availableSources = new Set(
    files.map((file) => normalizeSource(file.source)).filter(Boolean),
  );
  const nextReferences: ChatInputFileReference[] = [];

  for (const reference of references) {
    const source = normalizeSource(reference.source);
    const insertedText = reference.insertedText.trim();
    if (!source || !availableSources.has(source) || !insertedText) continue;

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
