# Poco Contribution Guide (PR & Development Standards)

This document describes the contribution process for the Poco repository and the development standards that must be followed when submitting code.

## 1. Standard Contribution Workflow

1. First, sync the latest code and create a branch from `main`.
2. Develop in a single-topic branch; avoid putting unrelated changes in the same PR.
3. Complete self-checks locally (see "Pre-commit Checks").
4. Push the branch and create a PR to `main`.
5. Maintainers will review and request changes.
6. Continue pushing to the same branch until the review passes and a maintainer merges it.

## 2. Branch and Commit Standards

It is recommended to use semantic branch names:

- `feat/<short-description>`
- `fix/<short-description>`
- `refactor/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

Commit messages should follow Conventional Commits (consistent with the repository's existing history):

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `docs: ...`
- `chore: ...`

Recommendations:

- Each commit should focus on one logical point.
- Avoid mixing refactoring, formatting, and feature changes in the same commit.

## 3. Pre-commit Checks

Run in the repository root:

```bash
pre-commit run --all-files
```

If you modified the frontend, also run:

```bash
cd frontend
pnpm lint
pnpm build
```

If you modified Python services (`backend`/`executor`/`executor_manager`), please install dependencies and verify the service can start:

```bash
cd <service>
uv sync
uv run python -m app.main
```

If you modified database models, handle migrations as follows (in the `backend` directory):

```bash
uv run -m alembic revision --autogenerate -m "description"
uv run -m alembic upgrade head
```

Then manually verify the auto-generated migration meets expectations.

## 4. PR Description Template

It is recommended to include at least the following in your PR description:

- Background and goals of the changes
- Main changes
- Affected areas (frontend/backend/executor/executor_manager)
- Local verification commands and results
- If UI changes: provide screenshots or recordings
- If database changes: provide migration and rollback instructions
- If breaking changes: clearly state upgrade considerations

## 5. Development Standards

### 5.1 General Standards

- Do not commit keys, tokens, private configuration, or any sensitive information.
- When adding new features, simultaneously update relevant documentation (README, docs, or API docs).
- Keep changes minimal; prioritize fixing root causes, avoid unrelated refactoring.

### 5.2 Python (Backend Services)

- Python version: `3.12+`
- Must write complete type annotations, prefer built-in generics: `list[T]`, `dict[str, Any]`, `X | None`.
- Code comments must be in English; Docstrings follow Google style.

Backend layering standards (`backend`):

- `repositories/` - Database CRUD only, no business logic.
- `services/` - Business orchestration and transaction management.
- `services/` returns SQLAlchemy Model or Pydantic Schema, not raw `dict[str, Any]`.
- Database sessions are created via FastAPI dependency injection at the API layer, then passed to services/repositories.

Exception handling standards (`backend`):

- Business errors use `AppException`.
- HTTP semantic errors use `HTTPException`.
- Do not catch generic `Exception` and wrap it as `HTTPException(500, ...)`.

### 5.3 Frontend (Next.js)

- Use Tailwind CSS v4 with design variables (`frontend/app/globals.css`).
- Do not hardcode colors, shadows, or border-radius; prefer design tokens (e.g., `var(--primary)`, `var(--shadow-md)`, `var(--radius)`).
- All user-facing text must go through i18n; do not write hardcoded strings.
- i18n related paths:
  - `frontend/lib/i18n/client.ts`
  - `frontend/lib/i18n/settings.ts`
  - `frontend/lib/i18n/locales/*/translation.json`

## 6. Review and Merge Criteria

Usually ready to merge when:

- Change goals are clear, PR description is complete.
- Local checks pass, and verification steps are reproducible.
- Code follows layering and style standards.
- Necessary documentation is updated.
- Review comments are addressed or consensus is reached.

Final merge is executed by repository maintainers.
