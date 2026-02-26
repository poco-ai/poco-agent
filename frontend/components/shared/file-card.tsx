import { FileText, File, Image as ImageIcon, Code } from "lucide-react";
import { memo } from "react";
import { BaseCard } from "./base-card";

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

const formatFileSize = (size: number | null | undefined): string => {
  if (!size) return "Unknown size";
  return size / 1024 > 1024
    ? `${(size / 1024 / 1024).toFixed(1)} MB`
    : `${Math.ceil(size / 1024)} KB`;
};

export function FileCard({
  file,
  onRemove,
  className,
  showRemove = true,
}: FileCardProps) {
  return (
    <BaseCard
      icon={<FileIcon file={file} />}
      title={file.name}
      subtitle={formatFileSize(file.size)}
      onRemove={onRemove}
      showRemove={showRemove}
      className={className}
    />
  );
}
