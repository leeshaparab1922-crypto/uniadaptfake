import { useLogout } from "../api/authApi";
import type { UserPublic } from "../types/auth";

export default function TopBar({ user }: { user: UserPublic }) {
  const logout = useLogout();
  return (
    <header className="flex items-center justify-between border-b bg-white px-4 py-2">
      <span className="text-sm text-gray-700">
        {user.full_name} ({user.role})
      </span>
      <button
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
        className="rounded border px-3 py-1 text-sm"
      >
        Log out
      </button>
    </header>
  );
}
