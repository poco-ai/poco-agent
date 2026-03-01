import * as React from "react";

interface UseFileDropUploadOptions {
  onFilesDrop: (files: File[]) => void | Promise<void>;
  disabled?: boolean;
}

function hasFiles(dataTransfer: DataTransfer | null): boolean {
  if (!dataTransfer) return false;
  return Array.from(dataTransfer.types).includes("Files");
}

function extractFiles(dataTransfer: DataTransfer | null): File[] {
  if (!dataTransfer) return [];
  return Array.from(dataTransfer.files);
}

/**
 * Tracks file drag state globally and forwards dropped files.
 * Used by composer/chat to show a full-screen drop hint overlay.
 */
export function useFileDropUpload({
  onFilesDrop,
  disabled = false,
}: UseFileDropUploadOptions) {
  const [isDragActive, setIsDragActive] = React.useState(false);
  const dragDepthRef = React.useRef(0);

  const resetDragState = React.useCallback(() => {
    dragDepthRef.current = 0;
    setIsDragActive(false);
  }, []);

  React.useEffect(() => {
    if (!disabled) return;
    resetDragState();
  }, [disabled, resetDragState]);

  React.useEffect(() => {
    const handleDragEnter = (event: DragEvent) => {
      if (disabled || !hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      dragDepthRef.current += 1;
      setIsDragActive(true);
    };

    const handleDragOver = (event: DragEvent) => {
      if (disabled || !hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = "copy";
      }
    };

    const handleDragLeave = (event: DragEvent) => {
      if (!hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      dragDepthRef.current = Math.max(0, dragDepthRef.current - 1);
      if (dragDepthRef.current === 0) {
        setIsDragActive(false);
      }
    };

    const handleDrop = (event: DragEvent) => {
      if (!hasFiles(event.dataTransfer)) return;
      event.preventDefault();
      const files = extractFiles(event.dataTransfer);
      resetDragState();
      if (disabled || files.length === 0) return;
      void onFilesDrop(files);
    };

    window.addEventListener("dragenter", handleDragEnter);
    window.addEventListener("dragover", handleDragOver);
    window.addEventListener("dragleave", handleDragLeave);
    window.addEventListener("drop", handleDrop);

    return () => {
      window.removeEventListener("dragenter", handleDragEnter);
      window.removeEventListener("dragover", handleDragOver);
      window.removeEventListener("dragleave", handleDragLeave);
      window.removeEventListener("drop", handleDrop);
    };
  }, [disabled, onFilesDrop, resetDragState]);

  return {
    isDragActive,
    resetDragState,
  };
}
