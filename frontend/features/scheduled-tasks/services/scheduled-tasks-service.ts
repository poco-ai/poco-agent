import { apiClient, API_ENDPOINTS } from "@/services/api-client";
import type {
  ScheduledTask,
  ScheduledTaskCreateInput,
  ScheduledTaskTriggerResponse,
  ScheduledTaskUpdateInput,
} from "@/features/scheduled-tasks/types";
import type { RunResponse } from "@/features/chat/types/api/run";

export const scheduledTasksService = {
  list: async (): Promise<ScheduledTask[]> => {
    return apiClient.get<ScheduledTask[]>(API_ENDPOINTS.scheduledTasks);
  },

  get: async (scheduledTaskId: string): Promise<ScheduledTask> => {
    return apiClient.get<ScheduledTask>(
      API_ENDPOINTS.scheduledTask(scheduledTaskId),
    );
  },

  create: async (input: ScheduledTaskCreateInput): Promise<ScheduledTask> => {
    return apiClient.post<ScheduledTask>(API_ENDPOINTS.scheduledTasks, input);
  },

  update: async (
    scheduledTaskId: string,
    input: ScheduledTaskUpdateInput,
  ): Promise<ScheduledTask> => {
    return apiClient.patch<ScheduledTask>(
      API_ENDPOINTS.scheduledTask(scheduledTaskId),
      input,
    );
  },

  remove: async (scheduledTaskId: string): Promise<Record<string, unknown>> => {
    return apiClient.delete<Record<string, unknown>>(
      API_ENDPOINTS.scheduledTask(scheduledTaskId),
    );
  },

  trigger: async (
    scheduledTaskId: string,
  ): Promise<ScheduledTaskTriggerResponse> => {
    return apiClient.post<ScheduledTaskTriggerResponse>(
      API_ENDPOINTS.scheduledTaskTrigger(scheduledTaskId),
      {},
    );
  },

  listRuns: async (scheduledTaskId: string): Promise<RunResponse[]> => {
    return apiClient.get<RunResponse[]>(
      API_ENDPOINTS.scheduledTaskRuns(scheduledTaskId),
    );
  },
};
