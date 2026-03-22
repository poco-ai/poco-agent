export type SourceKind =
  | "github"
  | "zip"
  | "system"
  | "manual"
  | "unknown"
  | "skill-creator"
  | "marketplace";

export interface SourceInfo {
  kind: SourceKind;
  market?: string | null;
  repo?: string | null;
  url?: string | null;
  ref?: string | null;
  filename?: string | null;
}
