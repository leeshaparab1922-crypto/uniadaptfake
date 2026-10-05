import AdminShell from "./components/AdminShell";
import TeacherShell from "./components/TeacherShell";
import TopBar from "./components/TopBar";
import { useAuth } from "./hooks/useAuth";
import Login from "./pages/Login";
import MySubjects from "./pages/student/MySubjects";

/**
 * Role-gated root: unauthenticated (or expired-session) visitors always
 * see `Login`; Admin sees `AdminShell`'s management screens; Student sees
 * only the read-only `MySubjects` view with zero mutate controls (BUS-001).
 * Teacher sees `TeacherShell` (Phase 2: content ingestion and versioning).
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
      {user.role === "TEACHER" && <TeacherShell />}
    </div>
  );
}
