"use client";

import * as React from "react";
import {
  closestCorners,
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  type DragEndEvent,
  type DragStartEvent,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import { sortableKeyboardCoordinates } from "@dnd-kit/sortable";

import {
  buildKanbanColumns,
  getNextMobileKanbanStatus,
} from "@/features/issues/lib/kanban-columns";
import { formatIssueStatus } from "@/features/issues/lib/issue-presentation";
import type {
  WorkspaceIssue,
  WorkspaceIssueStatus,
} from "@/features/issues/model/types";
import { useT } from "@/lib/i18n/client";
import { cn } from "@/lib/utils";

import { TeamKanbanColumn } from "./team-kanban-column";
import { TeamIssueCard } from "./team-issue-card";

interface TeamKanbanBoardProps {
  issues: WorkspaceIssue[];
  onOpenIssue: (issueId: string) => void;
  onMoveIssue: (
    issueId: string,
    status: WorkspaceIssueStatus,
    position: number,
  ) => void;
  isMovePending?: boolean;
}

export function TeamKanbanBoard({
  issues,
  onOpenIssue,
  onMoveIssue,
  isMovePending = false,
}: TeamKanbanBoardProps) {
  const { t } = useT("translation");
  const columns = React.useMemo(() => buildKanbanColumns(issues), [issues]);
  const [mobileStatus, setMobileStatus] = React.useState(
    getNextMobileKanbanStatus(undefined),
  );
  const [activeIssueId, setActiveIssueId] = React.useState<string | null>(null);
  const activeIssue = React.useMemo(
    () => issues.find((issue) => issue.issue_id === activeIssueId) ?? null,
    [activeIssueId, issues],
  );
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  React.useEffect(() => {
    setMobileStatus((currentStatus) => getNextMobileKanbanStatus(currentStatus));
  }, [columns]);

  const activeMobileColumn =
    columns.find((column) => column.status === mobileStatus) ?? columns[0];

  const resolveMove = React.useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over) {
        return null;
      }

      const activeId = String(active.id);
      const activeIssueMeta = active.data.current;
      const activeStatus = activeIssueMeta?.status as WorkspaceIssueStatus | undefined;
      if (!activeStatus) {
        return null;
      }

      const activeColumn = columns.find((column) => column.status === activeStatus);
      const activePosition =
        activeColumn?.issues.findIndex((issue) => issue.issue_id === activeId) ?? -1;
      if (activePosition < 0) {
        return null;
      }

      const overType = over.data.current?.type;
      if (overType === "column") {
        const targetStatus = over.data.current?.status as
          | WorkspaceIssueStatus
          | undefined;
        const targetColumn = columns.find((column) => column.status === targetStatus);
        if (!targetStatus || !targetColumn) {
          return null;
        }
        const targetPosition = targetColumn.issues.length;
        if (activeStatus === targetStatus && activePosition === targetPosition - 1) {
          return null;
        }
        return {
          issueId: activeId,
          status: targetStatus,
          position: targetPosition,
        };
      }

      if (overType === "issue") {
        const targetStatus = over.data.current?.status as
          | WorkspaceIssueStatus
          | undefined;
        const targetIssueId = over.data.current?.issueId as string | undefined;
        const targetColumn = columns.find((column) => column.status === targetStatus);
        const targetPosition =
          targetColumn?.issues.findIndex((issue) => issue.issue_id === targetIssueId) ??
          -1;
        if (!targetStatus || !targetIssueId || targetPosition < 0) {
          return null;
        }
        if (activeStatus === targetStatus && activePosition === targetPosition) {
          return null;
        }
        return {
          issueId: activeId,
          status: targetStatus,
          position: targetPosition,
        };
      }

      return null;
    },
    [columns],
  );

  const handleDragStart = React.useCallback(
    (event: DragStartEvent) => {
      setActiveIssueId(String(event.active.id));
    },
    [],
  );

  const handleDragCancel = React.useCallback(() => {
    setActiveIssueId(null);
  }, []);

  const handleDragEnd = React.useCallback(
    (event: DragEndEvent) => {
      setActiveIssueId(null);
      const nextMove = resolveMove(event);
      if (!nextMove) {
        return;
      }
      onMoveIssue(nextMove.issueId, nextMove.status, nextMove.position);
    },
    [onMoveIssue, resolveMove],
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragCancel={handleDragCancel}
      onDragEnd={handleDragEnd}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-2 md:hidden">
          {columns.map((column) => (
            <button
              key={column.status}
              type="button"
              onClick={() => setMobileStatus(column.status)}
              className={cn(
                "rounded-2xl border px-3 py-2 text-left transition",
                mobileStatus === column.status
                  ? "border-foreground/15 bg-accent/70 text-foreground"
                  : "border-border/70 bg-background text-muted-foreground hover:bg-muted/20",
              )}
            >
              <p className="text-sm font-medium">
                {formatIssueStatus(t, column.status)}
              </p>
              <p className="text-xs">{column.issues.length}</p>
            </button>
          ))}
        </div>

        <div className="md:hidden">
          <TeamKanbanColumn
            status={activeMobileColumn.status}
            issues={activeMobileColumn.issues}
            onOpenIssue={onOpenIssue}
            className={cn(isMovePending && "pointer-events-none")}
          />
        </div>

        <div className="hidden gap-4 overflow-x-auto pb-2 md:flex">
          {columns.map((column) => (
            <TeamKanbanColumn
              key={column.status}
              status={column.status}
              issues={column.issues}
              onOpenIssue={onOpenIssue}
              className={cn("w-[20rem] shrink-0", isMovePending && "pointer-events-none")}
            />
          ))}
        </div>
      </div>
      <DragOverlay>
        {activeIssue ? (
          <div className="w-[20rem]">
            <TeamIssueCard
              issue={activeIssue}
              onOpen={() => {}}
              disabled
              className="shadow-2xl ring-2 ring-primary/20"
            />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}
