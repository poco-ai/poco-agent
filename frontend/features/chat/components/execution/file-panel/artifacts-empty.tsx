import { File, Sparkles } from "lucide-react";
import { useT } from "@/lib/i18n/client";

/**
 * Empty state component for artifacts panel
 */
interface ArtifactsEmptyProps {
  sessionStatus?: "pending" | "running" | "completed" | "failed" | "canceled";
  workspaceExportStatus?: string | null;
}

/**
 * Empty state component for artifacts panel
 */
export function ArtifactsEmpty({
  sessionStatus,
  workspaceExportStatus,
}: ArtifactsEmptyProps) {
  const isRunning =
    sessionStatus === "running" ||
    sessionStatus === "pending" ||
    workspaceExportStatus === "pending";
  const { t } = useT("translation");

  if (isRunning) {
    return (
      <div className="flex items-center justify-center flex-1 h-full w-full bg-background/50">
        <div className="relative flex flex-col items-center justify-center">
          {/* Logo and Ripple Animation */}
          <div className="relative flex items-center justify-center mb-8">
            {/* Ripple rings - Neutral colors */}
            <div className="absolute size-20 rounded-full border border-foreground/20 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite]" />
            <div className="absolute size-32 rounded-full border border-foreground/10 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite_1s]" />

            {/* Center Logo/Icon */}
            <div className="relative z-10 bg-background p-4 rounded-full border border-border shadow-sm">
              <Sparkles className="size-8 text-foreground" />
            </div>
          </div>

          {/* Text */}
          <div className="text-center space-y-2">
            <h3 className="text-lg font-medium text-foreground">
              {t("artifacts.empty.creating")}
            </h3>
            <p className="text-xs text-muted-foreground/80">
              {t("artifacts.empty.working")}
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center flex-1 h-full w-full">
      <div className="text-center text-muted-foreground">
        <File className="size-12 mx-auto mb-3 opacity-50" />
        <p className="text-sm">{t("artifacts.empty.noChanges")}</p>
        <p className="text-xs mt-1">{t("artifacts.empty.description")}</p>
      </div>
    </div>
  );
}
