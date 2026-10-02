import AdminShell from "./components/AdminShell";
import TopBar from "./components/TopBar";
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import MySubjects from "./pages/student/MySubjects";

/**
 * Role-gated root: unauthenticated (or expired-session) visitors always
 * see `Login`; Admin sees `AdminShell`'s management screens; Student sees
 * only the read-only `MySubjects` view with zero mutate controls (BUS-001).
 * Teacher-specific screens are out of Phase 1's Section 43 scope (later
 * phases add them), so Teacher sees a placeholder for now.
 */
export default function App() {
  const { user, isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return <p className="p-6">Loading...</p>;
  }

  if (!isAuthenticated || !user) {
    return <Login />;
  }

  return (
    <div>
      <TopBar user={user} />
      {user.role === "ADMIN" && <AdminShell />}
      {user.role === "STUDENT" && <MySubjects />}
      {user.role === "TEACHER" && (
        <p className="p-6 text-sm text-gray-600">
          Teacher screens ship in a later phase (Section 43 Phase 2+).
        </p>
      )}
    </div>
  );
}
