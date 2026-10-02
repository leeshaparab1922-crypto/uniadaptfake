import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest } from "../api/client";
import Toaster from "../components/Toaster";
import HierarchyManager from "../pages/admin/HierarchyManager";
import PromotionTransfer from "../pages/admin/PromotionTransfer";
import StudentImport from "../pages/admin/StudentImport";
import SubjectCatalogue from "../pages/admin/SubjectCatalogue";
import { store } from "../store";
import { dismissNotification } from "../store/notificationsSlice";

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        {ui}
        <Toaster />
      </QueryClientProvider>
    </Provider>,
  );
}

function jsonResponse(status: number, body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  store.getState().notifications.forEach((n) => store.dispatch(dismissNotification(n.id)));
  vi.unstubAllGlobals();
});

describe("apiRequest error detail", () => {
  it("flattens FastAPI 422 validation lists into a readable message", async () => {
    fetchMock.mockReturnValueOnce(
      jsonResponse(422, {
        detail: [{ loc: ["body", "capacity"], msg: "Input should be greater than 0", type: "x" }],
      }),
    );
    await expect(apiRequest("/x", { method: "POST", body: {} })).rejects.toMatchObject({
      status: 422,
      message: "capacity: Input should be greater than 0",
    });
  });

  it("keeps string details as-is", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(409, { detail: "Duplicate code" }));
    const err = (await apiRequest("/x").catch((e: unknown) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Duplicate code");
  });
});

describe("admin forms feedback and input bounds", () => {
  it("HierarchyManager numeric inputs forbid zero/negative values", () => {
    renderWithProviders(<HierarchyManager />);
    for (const name of ["duration_semesters", "number", "capacity"]) {
      const input = document.querySelector(`input[name="${name}"]`) as HTMLInputElement;
      expect(input.min).toBe("1");
    }
  });

  it("SubjectCatalogue and PromotionTransfer inputs carry the backend minimums", () => {
    const { unmount } = renderWithProviders(<SubjectCatalogue />);
    for (const el of document.querySelectorAll('input[name="semester_no"]')) {
      expect((el as HTMLInputElement).min).toBe("1");
    }
    expect((document.querySelector('input[name="credits"]') as HTMLInputElement).min).toBe("0");
    unmount();
    renderWithProviders(<PromotionTransfer />);
    expect((document.querySelector('input[name="to_semester_no"]') as HTMLInputElement).min).toBe(
      "1",
    );
  });

  it("shows a success toast and resets the form after a successful create", async () => {
    fetchMock.mockReturnValueOnce(
      jsonResponse(201, { id: "inst-1", name: "Inst", timezone: "UTC" }),
    );
    renderWithProviders(<HierarchyManager />);
    const name = screen.getByPlaceholderText("Institute name") as HTMLInputElement;
    await userEvent.type(name, "Inst");
    await userEvent.click(screen.getByRole("button", { name: /add institute/i }));

    expect(await screen.findByTestId("toast-success")).toHaveTextContent("Institute created.");
    expect(name.value).toBe("");
  });

  it("surfaces the backend error detail (incl. 422) in an error toast", async () => {
    fetchMock.mockReturnValueOnce(
      jsonResponse(422, {
        detail: [{ loc: ["body", "name"], msg: "String should have at least 1 character" }],
      }),
    );
    renderWithProviders(<HierarchyManager />);
    await userEvent.type(screen.getByPlaceholderText("Institute name"), "Inst");
    await userEvent.click(screen.getByRole("button", { name: /add institute/i }));

    const toast = await screen.findByTestId("toast-error");
    expect(toast).toHaveTextContent("name: String should have at least 1 character");
  });

  it("shows an error toast when a promotion preview fails", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(400, { detail: "Target section is full" }));
    renderWithProviders(<PromotionTransfer />);
    await userEvent.type(screen.getByPlaceholderText(/student ids/i), "s1");
    await userEvent.type(screen.getByPlaceholderText(/target batch id/i), "b1");
    await userEvent.type(screen.getByPlaceholderText(/target semester/i), "2");
    await userEvent.type(screen.getByPlaceholderText(/target section id/i), "sec1");
    await userEvent.click(screen.getByRole("button", { name: /preview/i }));

    expect(await screen.findByTestId("toast-error")).toHaveTextContent("Target section is full");
  });
});

describe("StudentImport student list", () => {
  const emptyList = { items: [], total: 0, limit: 25, offset: 0 };
  const listBody = {
    items: [
      {
        id: "1",
        user_id: "u1",
        roll_number: "R1",
        department_id: "d",
        batch_id: "b",
        section_id: "sec",
        current_semester_no: 1,
        email: "s1@example.com",
        full_name: "Student One",
      },
    ],
    total: 1,
    limit: 25,
    offset: 0,
  };

  it("lists existing students beneath the import form", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(200, listBody));
    renderWithProviders(<StudentImport />);
    const list = await screen.findByTestId("student-list");
    await waitFor(() => expect(list).toHaveTextContent("Student One"));
    expect(list).toHaveTextContent("s1@example.com");
    expect(list).toHaveTextContent("Students (1)");
  });

  it("shows an empty state when there are no students", async () => {
    fetchMock.mockReturnValueOnce(jsonResponse(200, emptyList));
    renderWithProviders(<StudentImport />);
    expect(await screen.findByText(/no students yet/i)).toBeInTheDocument();
  });

  it("refreshes the list and toasts after a successful import", async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse(200, emptyList))
      .mockReturnValueOnce(jsonResponse(200, { created: 1, errors: [] }))
      .mockReturnValueOnce(jsonResponse(200, listBody));
    renderWithProviders(<StudentImport />);
    await screen.findByText(/no students yet/i);

    const file = new File(["x"], "students.csv", { type: "text/csv" });
    await userEvent.upload(screen.getByTestId("csv-file-input"), file);
    // jsdom does not see userEvent.upload files for `required` validation, so submit directly.
    fireEvent.submit(screen.getByTestId("csv-file-input").closest("form") as HTMLFormElement);

    expect(await screen.findByTestId("toast-success")).toHaveTextContent("Imported 1 student(s).");
    await waitFor(() =>
      expect(screen.getByTestId("student-list")).toHaveTextContent("Student One"),
    );
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("shows an error toast when the import request fails", async () => {
    fetchMock
      .mockReturnValueOnce(jsonResponse(200, emptyList))
      .mockReturnValueOnce(jsonResponse(400, { detail: "Only .csv uploads are accepted" }));
    renderWithProviders(<StudentImport />);
    await screen.findByText(/no students yet/i);
    await userEvent.upload(
      screen.getByTestId("csv-file-input"),
      new File(["x"], "s.csv", { type: "text/csv" }),
    );
    // jsdom does not see userEvent.upload files for `required` validation, so submit directly.
    fireEvent.submit(screen.getByTestId("csv-file-input").closest("form") as HTMLFormElement);
    expect(await screen.findByTestId("toast-error")).toHaveTextContent(
      "Only .csv uploads are accepted",
    );
  });
});
