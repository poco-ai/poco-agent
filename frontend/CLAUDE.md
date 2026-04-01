[Root](../CLAUDE.md) > **frontend**

# Frontend

> Next.js 16 web UI with feature-first architecture, i18n support (6 languages), and Tailwind CSS v4 design system.

## Changelog

| Date       | Action  | Summary                  |
| ---------- | ------- | ------------------------ |
| 2026-03-31 | Created | Initial module CLAUDE.md |

---

## Module Responsibilities

- Web UI for task creation, monitoring, and management
- Real-time chat interface with execution panels
- Capabilities management (skills, plugins, MCP, env vars, slash commands, sub-agents, personalization)
- Project organization and task history
- Scheduled tasks CRUD and management
- Memory management
- Multi-language support (en, zh, de, fr, ja, ru)
- Dark/light theme with design system
- Mobile-responsive layout

## Entry and Startup

- **Entry**: `app/page.tsx` -- Root page (redirect to localized home)
- **Root Layout**: `app/layout.tsx` -- ThemeProvider, StartupSplashGate, Toaster
- **Shell Layout**: `app/[lng]/(shell)/layout.tsx` -- AppShell with sidebar
- **Dev Server**: `pnpm dev` -> Next.js dev server

## Architecture: Feature-First Organization

### Route Structure

```
app/
  layout.tsx                         # Root layout
  page.tsx                           # Root redirect
  api/v1/[...path]/route.ts          # Proxy to Backend
  [lng]/
    layout.tsx                       # Locale layout
    page.tsx                         # Locale redirect
    loading.tsx
    (shell)/
      layout.tsx                     # AppShell (sidebar + content)
      home/page.tsx                  # Home page
      (chat)/
        chat/[id]/page.tsx           # Chat/execution page
      projects/[id]/page.tsx         # Project detail
      capabilities/
        page.tsx                     # Capabilities hub
        scheduled-tasks/
          page.tsx                   # Scheduled tasks list
          [taskId]/page.tsx          # Scheduled task detail
      memories/page.tsx              # Memories page
```

### Feature Modules

Each feature follows: `api/`, `components/` (or `ui/`), `hooks/`, `services/`, `types/`, `index.ts`

| Feature             | Path                        | Description                                                                                                         |
| ------------------- | --------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Chat**            | `features/chat/`            | Core chat interface, execution panels, message rendering, tool visualization, file/artifact viewers, model selector |
| **Home**            | `features/home/`            | Home page with model selector, quick actions, project cards                                                         |
| **Projects**        | `features/projects/`        | Project CRUD, task history, task management                                                                         |
| **Capabilities**    | `features/capabilities/`    | Hub for skills, plugins, MCP, env vars, slash commands, sub-agents, personalization, presets                        |
| **Scheduled Tasks** | `features/scheduled-tasks/` | CRUD for cron-based recurring tasks                                                                                 |
| **Memories**        | `features/memories/`        | Memory management UI                                                                                                |
| **Search**          | `features/search/`          | Global search                                                                                                       |
| **Settings**        | `features/settings/`        | App settings                                                                                                        |
| **Onboarding**      | `features/onboarding/`      | First-run experience                                                                                                |
| **Task Composer**   | `features/task-composer/`   | Task creation flow                                                                                                  |
| **User**            | `features/user/`            | User profile/management                                                                                             |
| **Voice**           | `features/voice/`           | Voice input                                                                                                         |
| **Connectors**      | `features/connectors/`      | External connectors                                                                                                 |
| **Attachments**     | `features/attachments/`     | File attachment handling                                                                                            |

### Component Layers

| Layer         | Path                 | Purpose                                                           |
| ------------- | -------------------- | ----------------------------------------------------------------- |
| UI Primitives | `components/ui/`     | 80+ shadcn/ui-based components (button, dialog, tabs, etc.)       |
| Shared        | `components/shared/` | Cross-feature components (markdown, cards, error boundary, theme) |
| Shell         | `components/shell/`  | App shell, sidebar, navigation                                    |

### Cross-Cutting

| Path                     | Purpose                                                      |
| ------------------------ | ------------------------------------------------------------ |
| `hooks/`                 | Global hooks (mobile detection, theme, pagination, language) |
| `lib/`                   | Utilities, i18n, errors, markdown, startup preload           |
| `services/api-client.ts` | Global API client                                            |
| `types/`                 | Global shared types                                          |

## API Proxy

`app/api/v1/[...path]/route.ts` proxies all API calls to Backend:

- Reads `BACKEND_URL` / `POCO_BACKEND_URL` / `POCO_API_URL` (default: `http://localhost:8000`)
- Strips hop-by-hop headers, adds forwarding headers
- Supports GET, POST, PUT, PATCH, DELETE, OPTIONS

## Key Dependencies

**Framework**: Next.js 16.1.1 (App Router), React 19.2.3, TypeScript 5

**UI**: Tailwind CSS v4, shadcn/ui (80+ components), Radix UI primitives, Lucide React icons, Motion animations

**Data/Forms**: react-hook-form + zod, @hookform/resolvers

**Visualization**: Recharts, Mermaid, Excalidraw, react-pdf, highlight.js, KaTeX

**i18n**: i18next, react-i18next, i18next-browser-languagedetector (6 languages)

**State/UX**: GSAP animations, Vaul drawer, Sonner toast, next-themes

## Key Configuration

| File                                      | Purpose                                                  |
| ----------------------------------------- | -------------------------------------------------------- |
| `package.json`                            | Dependencies, scripts                                    |
| `app/globals.css`                         | CSS variables (colors, shadows, radius) -- design system |
| `lib/i18n/settings.ts`                    | i18n configuration                                       |
| `lib/i18n/locales/{lng}/translation.json` | Translation files                                        |

## Internationalization

6 supported languages: English (`en`), Chinese (`zh`), German (`de`), French (`fr`), Japanese (`ja`), Russian (`ru`).

All user-facing text must use `useT()` hook:

```tsx
const { t } = useT();
<Button>{t("sidebar.newTask")}</Button>;
```

## Design System

Tailwind CSS v4 with CSS variables in `app/globals.css`:

- Colors: `var(--background)`, `var(--foreground)`, `var(--primary)`, `var(--border)`, etc.
- Shadows: `var(--shadow-sm)`, `var(--shadow-md)`, `var(--shadow-lg)`, etc.
- Border radius: `var(--radius)`

Do NOT hardcode colors or write raw CSS without using these variables.

## Testing

**Framework**: Vitest 4 + @testing-library/react + @testing-library/jest-dom + jsdom

| Command              | Purpose                           |
| -------------------- | --------------------------------- |
| `pnpm test`          | Run all tests                     |
| `pnpm test:watch`    | Watch mode                        |
| `pnpm test:coverage` | Coverage report (Istanbul)        |
| `pnpm test:ci`       | CI mode (JSON + default reporter) |

### Test Structure

| Layer       | Path                               | What's Tested                             |
| ----------- | ---------------------------------- | ----------------------------------------- |
| Unit        | `tests/lib/**/*.test.ts`           | Pure functions (utils, errors, clipboard) |
| Hook        | `tests/features/*/hooks/*.test.ts` | React hooks (renderHook + fakeTimers)     |
| Component   | `tests/components/**/*.test.tsx`   | UI components (render + userEvent)        |
| Integration | `tests/integration/**/*.test.ts`   | API client (fetch mocking)                |

### Key Files

| File               | Purpose                                               |
| ------------------ | ----------------------------------------------------- |
| `vitest.config.ts` | Vitest configuration (jsdom, globals, coverage)       |
| `tests/setup.ts`   | Global mocks (next/navigation, matchMedia, observers) |
| `tests/setup.d.ts` | Vitest globals type reference                         |

### Writing Tests

- Globals mode enabled: use `describe/it/expect/vi` without imports
- Use `@/*` path alias (same as source code)
- For React hooks: `import { renderHook, act } from "@testing-library/react"`
- For components: `import { render, screen } from "@testing-library/react"` + `import userEvent from "@testing-library/user-event"`

## Quality Gates

Before submitting changes:

1. `pnpm lint` must pass
2. `pnpm build` must pass
3. `pnpm test` must pass
4. Manually verify key flows: create task, chat execution, project switching, capabilities CRUD

## FAQ

**Q: How do I add a new feature module?**
A: Create `features/<name>/` with `api/`, `components/`, `hooks/`, `services/`, `types/`, `index.ts`. Export public API through `index.ts`.

**Q: How does the API proxy work?**
A: All `/api/v1/*` requests from the browser are caught by `app/api/v1/[...path]/route.ts` and forwarded to Backend.

**Q: How do I add a new language?**
A: Create `lib/i18n/locales/<code>/translation.json`, add the language to `lib/i18n/settings.ts`.

## Related Files

- `package.json` -- Dependencies and scripts
- `app/layout.tsx` -- Root layout
- `app/[lng]/(shell)/layout.tsx` -- Shell layout
- `app/api/v1/[...path]/route.ts` -- API proxy
- `lib/i18n/` -- i18n setup and translations
- `app/globals.css` -- Design system CSS variables
- `features/` -- All feature modules
- `components/` -- Shared components
