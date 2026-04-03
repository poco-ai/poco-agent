"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { History, ArrowRight } from "lucide-react";
import { useT } from "@/lib/i18n/client";
import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import { cn } from "@/lib/utils";

interface McpConnectionEvent {
  id: string;
  connection_id: string;
  run_id: string;
  from_state: string | null;
  to_state: string;
  event_source: string;
  error_message: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

interface McpConnection {
  id: string;
  server_name: string;
  state: string;
  health: string | null;
  attempt_count: number;
  last_error: string | null;
}

interface McpStateMachineCardProps {
  runId: string;
}

const POLL_INTERVAL_MS = 5_000;

const STATE_COLORS: Record<string, string> = {
  requested: "bg-muted text-muted-foreground",
  staged: "bg-blue-500/10 text-blue-600",
  launching: "bg-yellow-500/10 text-yellow-600",
  connected: "bg-green-500/10 text-green-600",
  failed: "bg-red-500/10 text-red-600",
  terminated: "bg-muted text-muted-foreground",
  degraded: "bg-amber-500/10 text-amber-600",
};

export function McpStateMachineCard({ runId }: McpStateMachineCardProps) {
  const { t } = useT("translation");
  const [connections, setConnections] = React.useState<McpConnection[]>([]);
  const [expanded, setExpanded] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await apiClient.get<McpConnection[]>(
          API_ENDPOINTS.runMcpConnections(runId),
          { cache: "no-store" },
        );
        if (!cancelled) setConnections(res ?? []);
      } catch {
        // silent
      }
    };
    void load();
    const timer = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [runId]);

  if (connections.length === 0) return null;

  return (
    <Card className="overflow-hidden">
      <CardHeader className="py-3 px-4">
        <CardTitle className="text-sm font-semibold flex items-center gap-2">
          <History className="size-4" />
          <span>{t("mcp.stateMachine.title", "MCP State History")}</span>
          <Badge variant="outline" className="text-xs ml-auto">
            {connections.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-4 pt-0 space-y-2">
        {connections.map((conn) => (
          <div key={conn.id} className="space-y-1">
            <button
              type="button"
              className="w-full flex items-center justify-between gap-2 text-xs p-2 rounded-md bg-muted/50 hover:bg-muted/80 transition-colors"
              onClick={() =>
                setExpanded((prev) => (prev === conn.id ? null : conn.id))
              }
            >
              <span className="font-mono truncate">{conn.server_name}</span>
              <div className="flex items-center gap-1.5 shrink-0">
                {conn.attempt_count > 1 && (
                  <Badge variant="outline" className="text-xs">
                    ×{conn.attempt_count}
                  </Badge>
                )}
                <Badge
                  variant="outline"
                  className={cn(
                    "text-xs",
                    STATE_COLORS[conn.state] ?? "bg-muted text-muted-foreground",
                  )}
                >
                  {conn.state}
                </Badge>
              </div>
            </button>

            {expanded === conn.id && (
              <div className="space-y-1">
                {conn.last_error && (
                  <div className="rounded-md bg-red-500/5 border border-red-500/20 px-3 py-2 text-xs text-red-600 font-mono">
                    {conn.last_error}
                  </div>
                )}
                <McpTransitionTimeline
                  runId={runId}
                  connectionId={conn.id}
                />
              </div>
            )}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

interface McpTransitionTimelineProps {
  runId: string;
  connectionId: string;
}

export function McpTransitionTimeline({
  runId,
  connectionId,
}: McpTransitionTimelineProps) {
  const { t } = useT("translation");
  const [events, setEvents] = React.useState<McpConnectionEvent[]>([]);

  React.useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    const load = async () => {
      try {
        const res = await apiClient.get<McpConnectionEvent[]>(
          API_ENDPOINTS.runMcpConnectionEvents(runId),
          { cache: "no-store" },
        );
        if (!cancelled) {
          const filtered = (res ?? []).filter(
            (ev: McpConnectionEvent) => ev.connection_id === connectionId,
          );
          setEvents(filtered);
        }
      } catch {
        // silent
      }
    };
    void load();
    const timer = setInterval(() => void load(), POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [runId, connectionId]);

  if (events.length === 0) return null;

  return (
    <ScrollArea className="max-h-[200px]">
      <div className="space-y-1 pr-2">
        {events.map((ev) => (
          <div key={ev.id} className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground/50 font-mono shrink-0">
              {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ""}
            </span>
            <div className="flex items-center gap-1 shrink-0">
              {ev.from_state && (
                <>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      STATE_COLORS[ev.from_state] ?? "",
                    )}
                  >
                    {ev.from_state}
                  </Badge>
                  <ArrowRight className="size-3 text-muted-foreground/50" />
                </>
              )}
              <Badge
                variant="outline"
                className={cn("text-xs", STATE_COLORS[ev.to_state] ?? "")}
              >
                {ev.to_state}
              </Badge>
            </div>
            <span className="text-muted-foreground/50 truncate">
              {t(`mcp.source.${ev.event_source}`, ev.event_source)}
            </span>
          </div>
        ))}
      </div>
    </ScrollArea>
  );
}
