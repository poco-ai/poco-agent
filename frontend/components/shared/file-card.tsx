import { FileText, File, Image as ImageIcon, Code, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { memo } from "react";

export type FileCardFile = {
  name: string;
  size?: number | null;
  content_type?: string | null;
};

interface FileCardProps {
  file: FileCardFile;
  onRemove?: () => void;
  className?: string;
  showRemove?: boolean;
}

const getFileIconType = (fileName: string, mimeType?: string | null) => {
  if (mimeType?.startsWith("image/")) return "image";
  const ext = fileName.split(".").pop()?.toLowerCase();
  if (
    ["js", "ts", "tsx", "jsx", "py", "java", "go", "rs", "c", "cpp"].includes(
      ext || "",
    )
  )
    return "code";
  if (["txt", "md", "json", "yml", "yaml"].includes(ext || "")) return "text";
  return "file";
};

const FileIcon = memo(({ file }: { file: FileCardFile }) => {
  const iconType = getFileIconType(file.name, file.content_type);

  if (iconType === "image") return <ImageIcon className="size-4" />;
  if (iconType === "code") return <Code className="size-4" />;
  if (iconType === "text") return <FileText className="size-4" />;
  return <File className="size-4" />;
});
FileIcon.displayName = "FileIcon";

export function FileCard({
  file,
  onRemove,
  className,
  showRemove = true,
}: FileCardProps) {
  return (
    <div
      className={cn(
        "group relative flex items-center gap-2 rounded-lg border border-border bg-card p-2 text-sm shadow-sm transition-all hover:shadow-md",
        className,
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
        <FileIcon file={file} />
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <p className="truncate font-medium text-foreground" title={file.name}>
          {file.name}
        </p>
        <p className="text-xs text-muted-foreground">
          {file.size
            ? file.size / 1024 > 1024
              ? `${(file.size / 1024 / 1024).toFixed(1)} MB`
              : `${Math.ceil(file.size / 1024)} KB`
            : "Unknown size"}
        </p>
      </div>

      {showRemove && onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute -right-2 -top-2 hidden size-5 items-center justify-center rounded-full bg-destructive text-destructive-foreground shadow-sm transition-opacity group-hover:flex hover:bg-destructive/90"
          type="button"
        >
          <X className="size-3" />
        </button>
      )}
    </div>
  );
}
