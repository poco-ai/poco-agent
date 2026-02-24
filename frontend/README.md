# Poco Frontend

Poco frontend is a Next.js 16 + React 19 application for task creation, agent execution monitoring, and capability management.

## Tech stack

- Next.js 16 (App Router)
- React 19 + TypeScript
- Tailwind CSS v4
- shadcn/ui
- i18next based internationalization
- pnpm

## Run locally

```bash
pnpm install
pnpm dev
```

Open `http://localhost:3000`.

## Common commands

```bash
pnpm dev
pnpm build
pnpm start
pnpm lint
```

## Environment

Frontend talks to backend through the Next.js proxy route at `app/api/v1/[...path]/route.ts`.

Useful variables:

- `BACKEND_URL`
- `POCO_BACKEND_URL`
- `POCO_API_URL`
- `NEXT_PUBLIC_API_URL`

## Architecture

Quick map:

- `app/`: routes + layouts + global styles
- `components/ui`: reusable UI primitives
- `components/shared`: feature-agnostic shared components
- `components/shell`: application shell & layout composition (may depend on `features/*`)
- `features/*`: domain modules
- `hooks/`: shared React hooks
- `lib/`: shared runtime utilities
- `services/`: API client and cross-feature service modules
- `types/`: global TypeScript types

## i18n

All user-facing strings should be translated via i18n keys.

Locale files:

- `lib/i18n/locales/en/translation.json`
- `lib/i18n/locales/zh/translation.json`
