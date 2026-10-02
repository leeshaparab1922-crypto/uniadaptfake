import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import Login from "../pages/Login";

const mockMutate = vi.fn();
const mockUseLogin = vi.fn(() => ({
  mutate: mockMutate,
  isPending: false,
  isError: false,
  error: null as Error | null,
}));
vi.mock("../api/authApi", () => ({
  useLogin: () => mockUseLogin(),
}));

describe("Login page", () => {
  it("submits email/password to the login mutation", async () => {
    render(<Login />);
    await userEvent.type(screen.getByLabelText(/email/i), "admin@example.com");
    await userEvent.type(screen.getByLabelText(/password/i), "Secret123!");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(mockMutate).toHaveBeenCalledWith({ email: "admin@example.com", password: "Secret123!" });
  });

  it("shows a generic error message on login failure, never a raw stack trace", () => {
    mockUseLogin.mockReturnValueOnce({
      mutate: mockMutate,
      isPending: false,
      isError: true,
      error: new Error("Invalid credentials or account unavailable."),
    });
    render(<Login />);
    expect(screen.getByRole("alert")).toHaveTextContent(
      /invalid credentials or account unavailable/i,
    );
  });
});
