import test from "node:test";
import assert from "node:assert/strict";

import { submitScheduledTask } from "./task-submit-api.ts";
import { scheduledTasksService } from "../../scheduled-tasks/api/scheduled-tasks-api.ts";

test("submitScheduledTask preserves false capability overrides in config", async () => {
  const originalCreate = scheduledTasksService.create;
  let payload: unknown = null;

  scheduledTasksService.create = async (nextPayload) => {
    payload = nextPayload;
    return { scheduled_task_id: "task-1" } as never;
  };

  try {
    await submitScheduledTask({
      prompt: "Run a task",
      mode: "task",
      options: {
        repo_url: " https://example.com/repo ",
        browser_enabled: false,
        memory_enabled: false,
      },
    });
  } finally {
    scheduledTasksService.create = originalCreate;
  }

  assert.deepEqual(payload, {
    name: "Run a task",
    cron: "*/5 * * * *",
    timezone: "UTC",
    prompt: "Run a task",
    enabled: true,
    reuse_session: true,
    project_id: undefined,
    config: {
      repo_url: "https://example.com/repo",
      git_branch: "main",
      browser_enabled: false,
      memory_enabled: false,
    },
  });
});
