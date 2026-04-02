"use client";

export interface PickedLocalDirectory {
  displayName: string;
  hostPath: string | null;
}

interface DirectoryPickerHandle {
  name: string;
}

interface DirectoryPickerWindow extends Window {
  showDirectoryPicker?: () => Promise<DirectoryPickerHandle>;
}

async function resolveDirectoryPath(name: string): Promise<string | null> {
  try {
    const res = await fetch(
      `/api/resolve-directory?name=${encodeURIComponent(name)}`,
    );
    if (!res.ok) {
      return null;
    }
    const data: { paths: string[] } = await res.json();
    return data.paths.length === 1 ? data.paths[0] : null;
  } catch {
    return null;
  }
}

export function supportsNativeDirectoryPicker(): boolean {
  if (typeof window === "undefined") {
    return false;
  }
  return (
    typeof (window as DirectoryPickerWindow).showDirectoryPicker === "function"
  );
}

export async function pickLocalDirectory(): Promise<PickedLocalDirectory | null> {
  if (!supportsNativeDirectoryPicker()) {
    return null;
  }

  const handle = await (
    window as DirectoryPickerWindow
  ).showDirectoryPicker?.();
  if (!handle) {
    return null;
  }

  const displayName = handle.name;
  const hostPath = await resolveDirectoryPath(displayName);
  return {
    displayName,
    hostPath,
  };
}
