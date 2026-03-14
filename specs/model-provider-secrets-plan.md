# Model Provider Secrets Plan

## Goals

- Support both system preset credentials and user-provided credentials.
- Show one of three states per provider in the frontend settings page:
  - `Unconfigured`
  - `Preset Service`
  - `Custom`
- Store secrets only in the backend with symmetric encryption.
- Support Anthropic, OpenAI, GLM, MiniMax, and DeepSeek.
- Unify home/chat model selection against one backend-driven model catalog.

## Current State

- Home model selection is real: it reads `/api/v1/models` and sends `config.model`.
- Chat model selection is mock/static and is not wired to backend model metadata.
- Settings model configuration is mock/local state only.
- Backend already stores env var secrets as encrypted ciphertext in `user_env_vars`.
- Executor Manager currently assumes a global Anthropic credential and injects only
  `ANTHROPIC_*` into executor containers.
- Real auth is not implemented yet. Backend resolves the current user from
  `X-User-Id` and falls back to `default`.

## Provider Credential Rules

- Reuse encrypted env var storage instead of creating a new secrets table.
- Keep separate env keys per provider:
  - `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`
  - `OPENAI_API_KEY`, `OPENAI_BASE_URL`
  - `GLM_API_KEY`, `GLM_BASE_URL`
  - `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`
  - `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`
- Credential precedence:
  - user-level key overrides system-level key
  - user-level base URL overrides system-level base URL
  - if neither base URL exists, fall back to provider default
- Provider state rules:
  - `Custom`: user-level key exists
  - `Preset Service`: no user-level key, system-level key exists
  - `Unconfigured`: neither exists

## Provider Defaults

- Anthropic: `https://api.anthropic.com`
- OpenAI: `https://api.openai.com/v1`
- GLM: `https://open.bigmodel.cn/api/paas/v4/`
- MiniMax: `https://api.minimaxi.com/v1`
- DeepSeek: `https://api.deepseek.com`

## Runtime Execution Strategy

- `/api/v1/models` should return structured provider and model metadata.
- Frontend settings should write secrets through existing env var APIs and never
  persist plaintext locally.
- Executor Manager should resolve the selected model's provider and construct
  runtime-only `env_overrides`.
- Executor should apply `env_overrides` only for the current run and restore the
  process environment afterwards.
- Anthropic models continue to use `ANTHROPIC_*`.
- OpenAI-compatible providers should be mapped into runtime `OPENAI_*` values:
  - OpenAI
  - GLM
  - MiniMax
  - DeepSeek

## Frontend Behavior

- Settings page shows provider status and editable key/base URL controls.
- Saved secret inputs must be cleared after submit and must never be rehydrated.
- Home and chat selectors must share the same backend model catalog.
- Existing sessions may switch the default model only for subsequent runs.
- Models requiring unavailable credentials should be disabled or clearly marked.

## Auth Constraint

- The current user system is only soft-scoped by `X-User-Id`.
- Without real auth, requests that omit `X-User-Id` all share the `default` user.
- This does not block implementation, but it means "user custom credentials"
  are only truly isolated when the caller provides a stable user identifier.
