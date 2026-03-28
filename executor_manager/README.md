# Executor Manager

Executor Manager is the runtime dispatcher for Poco.

## Primary Dispatch Model

- Backend owns durable session and run state.
- Backend's run queue is the single source of truth for dispatchable work.
- `RunPullService` claims queued runs from backend and performs runtime dispatch.
- Executor Manager stages runtime assets, allocates or reuses containers, and calls executor.
- APScheduler is used for polling and maintenance jobs, not as the primary execution state for user-created tasks.

## What Remains in APScheduler

- run-queue polling jobs for `RunPullService`
- scheduled-task dispatch polling
- optional maintenance jobs such as cleanup
