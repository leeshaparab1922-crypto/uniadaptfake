import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import MySubjects from "../pages/student/MySubjects";

const mockUseMyEnrollments = vi.fn();
vi.mock("../api/enrollmentApi", () => ({
  useMyEnrollments: () => mockUseMyEnrollments(),
}));

describe("MySubjects (FR-STU-001, BUS-001)", () => {
  it("renders the enrolled subject list with zero mutate controls", () => {
    mockUseMyEnrollments.mockReturnValue({
      data: [
        {
          id: "e1",
          subject_instance_id: "si1",
          elective_group_id: null,
          status: "ACTIVE",
          auto_allocated: true,
          effective_from: "2024-08-01",
          effective_to: null,
        },
      ],
      isLoading: false,
      isError: false,
    });
    render(<MySubjects />);
    expect(screen.getByTestId("my-subjects-list")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("form")).not.toBeInTheDocument();
  });

  it("shows a loading state", () => {
    mockUseMyEnrollments.mockReturnValue({ data: undefined, isLoading: true, isError: false });
    render(<MySubjects />);
    expect(screen.getByText(/loading your subjects/i)).toBeInTheDocument();
  });

  it("shows an error state without exposing internals", () => {
    mockUseMyEnrollments.mockReturnValue({ data: undefined, isLoading: false, isError: true });
    render(<MySubjects />);
    expect(screen.getByRole("alert")).toHaveTextContent(/could not load your subjects/i);
  });
});
