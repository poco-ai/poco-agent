"use client";

import * as React from "react";
import type { TaskHistoryItem } from "../model/types";

export function useProjectTasks(
  initialTasksFn?: () => TaskHistoryItem[],
  projectId?: string,
) {
  // 初始化任务列表
  const [tasks, setTasks] = React.useState<TaskHistoryItem[]>(() => {
    if (initialTasksFn) {
      const allTasks = initialTasksFn();
      // 如果指定了projectId，只返回该项目的任���
      if (projectId) {
        return allTasks.filter((task) => task.projectId === projectId);
      }
      return allTasks;
    }
    return [];
  });

  // 添加任务
  const addTask = React.useCallback(
    (title: string, metadata?: Partial<TaskHistoryItem>) => {
      const newTask: TaskHistoryItem = {
        id: `task-${Date.now()}`,
        title,
        status: "pending",
        timestamp: metadata?.timestamp || new Date().toISOString(),
        projectId: metadata?.projectId || projectId || null,
      };

      setTasks((prev) => [newTask, ...prev]);
      return newTask;
    },
    [projectId],
  );

  // 删除任务
  const removeTask = React.useCallback((taskId: string) => {
    setTasks((prev) => prev.filter((task) => task.id !== taskId));
  }, []);

  // 更新任务项目关联
  const updateTaskProject = React.useCallback(
    (taskId: string, newProjectId: string | null) => {
      setTasks((prev) =>
        prev.map((task) =>
          task.id === taskId ? { ...task, projectId: newProjectId } : task,
        ),
      );
    },
    [],
  );

  // 重命名任务
  const renameTask = React.useCallback((taskId: string, newName: string) => {
    setTasks((prev) =>
      prev.map((task) =>
        task.id === taskId ? { ...task, title: newName } : task,
      ),
    );
  }, []);

  return {
    taskHistory: tasks,
    addTask,
    removeTask,
    updateTaskProject,
    renameTask,
  };
}
