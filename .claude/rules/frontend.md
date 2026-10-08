---
description: Frontend (React/TypeScript) coding standards, structure, and testing rules for UniAdapt AI.
paths:
  - "frontend/**"
---

# UniAdapt AI — Frontend Rules

## Stack pin

React 18, TypeScript, Tailwind, Redux Toolkit, React Query, Recharts. See
`.claude/rules/general.md` for the full fixed-stack rule.

## Project structure (starting convention)

```
frontend/
└── src/
    ├── components/
    ├── pages/
    ├── features/
    ├── store/
    ├── api/
    ├── hooks/
    └── types/
```

Colocate tests as `*.test.tsx` next to the component, or under
`frontend/src/**/__tests__/`. Same "starting convention" caveat as backend —
Phase 1 may adjust with justification documented in `plan.md`.

## Naming conventions

- PascalCase for components and their files (`StudentDashboard.tsx`).
- camelCase for functions, variables, and hooks (`useMasteryScore`).
- Redux slices named `<domain>Slice.ts`.
- React Query owns all server state. Redux Toolkit is reserved for
  client-only/global UI state — never duplicate server state into Redux.

## Testing (NFR-TST-002)

- Vitest + React Testing Library.
- One test file per non-trivial component/hook.
- Integration tests for role-gated views (Admin/Teacher/Student) confirming
  role-based rendering and API-call scoping.

## Security-relevant frontend rules

- The JWT travels in an httpOnly, Secure, SameSite=Strict cookie with a
  double-submit CSRF token (ADR-0001, `docs/decisions/`). Frontend code never
  reads, stores, or logs the JWT, and sends `X-CSRF-Token` on every
  state-changing request. Still flag XSS exposure as a review point.
- Never log tokens or PII to the console in production builds.
- Mirror the 25MB/MIME upload constraints client-side as a UX pre-check —
  this is never a substitute for server-side enforcement.

## Lint / format / test tools

- **ESLint** — with TypeScript, React, and Hooks plugins, flat config
  (recommended since this is greenfield and flat config is ESLint's current
  direction).
- **Prettier** — formatting.
- **Vitest** (+ `@testing-library/react`, jsdom) — testing.

These are not yet configured in the repo (no `package.json` exists). When
Phase 1 scaffolds `frontend/`, it should add:

- `package.json` scripts: `lint`, `format`, `test`.
- An ESLint flat config file.
- A Prettier config file.
- A Vitest config file.
