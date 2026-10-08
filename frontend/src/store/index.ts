import { configureStore } from "@reduxjs/toolkit";

import notifications from "./notificationsSlice";

/**
 * Redux Toolkit store - reserved for genuine client-only/global UI state
 * (`.claude/rules/frontend.md`). The current user/session is server state
 * and lives exclusively in React Query (`hooks/useAuth.ts`), never mirrored
 * here. The only slice today is transient toast notifications, which are
 * pure client-side UI state.
 */
export const store = configureStore({
  reducer: { notifications },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
