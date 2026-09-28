import { configureStore } from "@reduxjs/toolkit";

/**
 * Redux Toolkit store - reserved for genuine client-only/global UI state
 * (`.claude/rules/frontend.md`). Phase 1 has no such state: the current
 * user/session is server state and lives exclusively in React Query
 * (`hooks/useAuth.ts`), never mirrored here. This store stays wired up
 * (per Section 5's fixed stack) for later phases that do need client-only
 * UI state, without duplicating anything React Query already owns.
 */
export const store = configureStore({
  reducer: {},
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
