import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { describe, expect, it, vi } from "vitest";

import App from "../App";
import { store } from "../store";

function renderApp() {
  const queryClient = new QueryClient();
  return render(
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </Provider>,
  );
}

const mockUseAuth = vi.fn();
vi.mock("../hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../api/enrollmentApi", () => ({
  useMyEnrollments: () => ({ data: [], isLoading: false, isError: false }),
}));

vi.mock("../api/authApi", () => ({
  useMe: () => ({ data: null, isLoading: false, isError: false }),
  useLogin: () => ({ mutate: vi.fn(), isPending: false, isError: false }),
  useLogout: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe("App role-gated rendering", () => {
  it("shows the login form when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: false, isAuthenticated: false });
    renderApp();
    expect(screen.getByTestId("login-form")).toBeInTheDocument();
  });

  it("shows the login form when the session has expired (isAuthenticated false, user null)", () => {
    mockUseAuth.mockReturnValue({ user: null, isLoading: false, isAuthenticated: false });
    renderApp();
    expect(screen.getByTestId("login-form")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-nav")).not.toBeInTheDocument();
  });

  it("shows Admin management screens (with mutate controls) for an ADMIN user", () => {
    mockUseAuth.mockReturnValue({
      user: { id: "1", email: "a@example.com", full_name: "Admin", role: "ADMIN", is_active: true },
      isLoading: false,
      isAuthenticated: true,
    });
    renderApp();
    expect(screen.getByTestId("admin-nav")).toBeInTheDocument();
    expect(screen.getByTestId("hierarchy-manager")).toBeInTheDocument();
    // Admin screens do contain mutate controls (buttons that submit forms).
    expect(screen.getByRole("button", { name: /add institute/i })).toBeInTheDocument();
  });

  it("shows only the read-only subject list (no mutate controls) for a STUDENT user", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "2",
        email: "s@example.com",
        full_name: "Student",
        role: "STUDENT",
        is_active: true,
      },
      isLoading: false,
      isAuthenticated: true,
    });
    renderApp();
    expect(screen.getByTestId("my-subjects-list")).toBeInTheDocument();
    expect(screen.queryByTestId("admin-nav")).not.toBeInTheDocument();
    // No add/drop/mutate button anywhere in the Student's tree (BUS-001).
    expect(screen.queryAllByRole("button")).toHaveLength(1); // only the "Log out" button in TopBar
  });

  it("shows a placeholder (no admin/student mutate controls) for a TEACHER user", () => {
    mockUseAuth.mockReturnValue({
      user: {
        id: "3",
        email: "t@example.com",
        full_name: "Teacher",
        role: "TEACHER",
        is_active: true,
      },
      isLoading: false,
      isAuthenticated: true,
    });
    renderApp();
    expect(screen.queryByTestId("admin-nav")).not.toBeInTheDocument();
    expect(screen.queryByTestId("my-subjects-list")).not.toBeInTheDocument();
  });
});
