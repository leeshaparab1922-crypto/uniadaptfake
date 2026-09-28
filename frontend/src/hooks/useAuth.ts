import { useMe } from "../api/authApi";

/** Resolves the current session via React Query (`GET /auth/me`, which
 * relies solely on the httpOnly cookie). React Query is the single source
 * of truth for this server state - it is never mirrored into Redux
 * (`.claude/rules/frontend.md`: "never duplicate server state into
 * Redux"). Redux Toolkit remains reserved for genuine client-only/global
 * UI state, of which Phase 1 has none yet. */
export function useAuth() {
  const { data: user, isLoading, isError } = useMe();

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: Boolean(user) && !isError,
  };
}
