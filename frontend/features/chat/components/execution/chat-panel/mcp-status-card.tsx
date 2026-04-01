"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Server, Check, X, AlertTriangle } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import type { McpStatusItem } from "@/features/chat/types";

interface McpStatusCardProps {
  mcpStatuses: McpStatusItem[];
}

export function McpStatusCard({ mcpStatuses }: McpStatusCardProps) {
  const { t } = useT("translation");

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "connected":
        return <Check className="size-3 text-primary" />;
      case "requested":
      case "staged":
      case "launching":
        return <AlertTriangle className="size-3 text-chart-4" />;
      case "terminated":
      case "disconnected":
        return <X className="size-3 text-muted-foreground" />;
      case "degraded":
        return <AlertTriangle className="size-3 text-amber-500" />;
      default:
        return <AlertTriangle className="size-3 text-chart-4" />;
    }
  };

  const getStatusVariant = (
    status: string,
  ): "default" | "secondary" | "destructive" | "outline" => {
    switch (status) {
      case "connected":
        return "outline";
      case "error":
        return "destructive";
      case "degraded":
        return "outline";
      default:
        return "secondary";
    }
  };

  return (
    <Card className="overflow-hidden flex flex-col h-full">
      <CardHeader className="py-3 px-4 shrink-0">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <Server className="size-4" />
          <span>{t("mcp.title")}</span>
          <Badge variant="outline" className="text-xs ml-auto">
            {mcpStatuses.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0">
        <ScrollArea className="max-h-[180px]">
          <div className="space-y-2 pr-2">
            {mcpStatuses.map((mcp, index) => (
              <div
                key={index}
                className="flex items-center justify-between gap-2 text-xs p-2 rounded-md bg-muted/50 shrink-0"
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {getStatusIcon(mcp.status)}
                  <span className="font-mono truncate">{mcp.server_name}</span>
                </div>
                <Badge
                  variant={getStatusVariant(mcp.status)}
                  className="flex-shrink-0 text-xs"
                >
                  {t(`mcp.${mcp.status}`)}
                </Badge>
              </div>
            ))}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
