import test from "node:test";
import assert from "node:assert/strict";

import { createProjectAction, updateProjectAction } from "./project-actions.ts";
import { projectsService } from "../api/projects-api.ts";

test("createProjectAction preserves explicit null project defaults", async () => {
  const originalCreateProject = projectsService.createProject;
  let payload: unknown = null;

  projectsService.createProject = async (nextPayload) => {
    payload = nextPayload;
    return { id: "project-1" } as never;
  };

  try {
    await createProjectAction({
      name: "Docs",
      description: null,
      default_model: null,
      default_preset_id: null,
      local_mounts: null,
      repo_url: null,
      git_branch: null,
      git_token_env_key: null,
    });
  } finally {
    projectsService.createProject = originalCreateProject;
  }

  assert.deepEqual(payload, {
    name: "Docs",
    description: null,
    default_model: null,
    default_preset_id: null,
    local_mounts: null,
    repo_url: null,
    git_branch: null,
    git_token_env_key: null,
  });
});

test("updateProjectAction preserves explicit null project defaults", async () => {
  const originalUpdateProject = projectsService.updateProject;
  let payload: unknown = null;

  projectsService.updateProject = async (_projectId, nextPayload) => {
    payload = nextPayload;
    return { id: "project-1" } as never;
  };

  try {
    await updateProjectAction({
      projectId: "project-1",
      description: null,
      default_model: null,
      default_preset_id: null,
      local_mounts: null,
      repo_url: null,
      git_branch: null,
      git_token_env_key: null,
    });
  } finally {
    projectsService.updateProject = originalUpdateProject;
  }

  assert.deepEqual(payload, {
    name: undefined,
    description: null,
    default_model: null,
    default_preset_id: null,
    local_mounts: null,
    repo_url: null,
    git_branch: null,
    git_token_env_key: null,
  });
});
