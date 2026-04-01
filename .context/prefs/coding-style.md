# Coding Style Guide

> 此文件定义团队编码规范，所有 LLM 工具在修改代码时必须遵守。
> 提交到 Git，团队共享。

## General

- Prefer small, reviewable changes; avoid unrelated refactors.
- Keep functions short (<50 lines); avoid deep nesting (≤3 levels).
- Name things explicitly; no single-letter variables except loop counters.
- Handle errors explicitly; never swallow errors silently.

## Python

- **Formatter/Linter**: Ruff (configured in root `pyproject.toml`)
- **Type Checker**: Pyrefly
- **Style**: Type annotations required (Python 3.12+ syntax: `list[T]`, `T | None`)
- **Comments**: English only, concise
- **Docstrings**: Google Python Style Guide
- **Layering**: API → Service → Repository (strict separation)

## TypeScript / React

- **Linter**: ESLint with Next.js config
- **Formatter**: Prettier
- **Styling**: Tailwind CSS v4 with CSS variables
- **i18n**: All user-facing text via `useT()` hook
- **Architecture**: Feature-first organization (`features/<name>/`)
- No `any` types; use explicit interfaces/types

## Git Commits

- Conventional Commits, imperative mood.
- Atomic commits: one logical change per commit.

## Testing

- Every feat/fix MUST include corresponding tests.
- Coverage must not decrease.
- Fix flow: write failing test FIRST, then fix code.

## Security

- Never log secrets (tokens/keys/cookies/JWT).
- Validate inputs at trust boundaries.
- No `any` types in frontend; use explicit interfaces/types.
