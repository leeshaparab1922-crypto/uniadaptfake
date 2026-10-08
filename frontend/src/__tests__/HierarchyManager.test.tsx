import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import Toaster from "../components/Toaster";
import HierarchyManager from "../pages/admin/HierarchyManager";
import { store } from "../store";
import { dismissNotification } from "../store/notificationsSlice";

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <HierarchyManager />
        <Toaster />
      </QueryClientProvider>
    </Provider>,
  );
}

function json(status: number, body: unknown) {
  return Promise.resolve(
    new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }),
  );
}

const inst = { id: "i1", name: "Alpha College", timezone: "Asia/Kolkata" };
const dept = { id: "d1", institute_id: "i1", code: "CSE", name: "Computer Science" };

const fetchMock = vi.fn();

/** Route by URL so the test does not depend on call order. */
function route(handlers: Record<string, () => Promise<Response>>) {
  fetchMock.mockImplementation((url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url.replace("http://localhost:8000", "")}`;
    const handler = handlers[key];
    if (!handler) throw new Error(`unexpected request: ${key}`);
    return handler();
  });
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  store.getState().notifications.forEach((n) => store.dispatch(dismissNotification(n.id)));
  vi.unstubAllGlobals();
});

const BASE = "/admin/academic-structure";

describe("HierarchyManager list view", () => {
  it("lists saved institutes on load and shows hints for deeper levels", async () => {
    route({ [`GET ${BASE}/institutes`]: () => json(200, [inst]) });
    renderPage();
    expect(await screen.findByText("Alpha College (Asia/Kolkata)")).toBeInTheDocument();
    expect(screen.getByTestId("department-list")).toHaveTextContent(
      "Select an institute to see its departments.",
    );
  });

  it("shows an empty state when there are no institutes", async () => {
    route({ [`GET ${BASE}/institutes`]: () => json(200, []) });
    renderPage();
    expect(await screen.findByText("No institutes yet.")).toBeInTheDocument();
  });

  it("shows an error instead of the empty state when a list fails to load", async () => {
    route({ [`GET ${BASE}/institutes`]: () => json(500, { detail: "Database unavailable" }) });
    renderPage();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load institutes: Database unavailable",
    );
    expect(screen.queryByText("No institutes yet.")).not.toBeInTheDocument();
  });

  it("selecting an existing institute enables and lists its departments", async () => {
    route({
      [`GET ${BASE}/institutes`]: () => json(200, [inst]),
      [`GET ${BASE}/departments?institute_id=i1`]: () => json(200, [dept]),
    });
    renderPage();
    // The department form stays disabled until a parent institute is picked.
    expect(
      (document.querySelector('input[placeholder="Dept code"]') as HTMLInputElement).disabled,
    ).toBe(true);

    await userEvent.click(
      await screen.findByRole("button", { name: "Alpha College (Asia/Kolkata)" }),
    );

    expect(await screen.findByText("CSE - Computer Science")).toBeInTheDocument();
    expect(
      (document.querySelector('input[placeholder="Dept code"]') as HTMLInputElement).disabled,
    ).toBe(false);
    expect(screen.getByRole("button", { name: /add department/i })).toBeEnabled();
  });

  it("refreshes the list after a successful create", async () => {
    let created = false;
    route({
      [`GET ${BASE}/institutes`]: () => json(200, created ? [inst] : []),
      [`POST ${BASE}/institutes`]: () => {
        created = true;
        return json(201, inst);
      },
      [`GET ${BASE}/departments?institute_id=i1`]: () => json(200, []),
    });
    renderPage();
    await screen.findByText("No institutes yet.");
    await userEvent.type(screen.getByPlaceholderText("Institute name"), "Alpha College");
    await userEvent.click(screen.getByRole("button", { name: /add institute/i }));

    expect(await screen.findByTestId("toast-success")).toHaveTextContent("Institute created.");
    expect(await screen.findByText("Alpha College (Asia/Kolkata)")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("No departments yet.")).toBeInTheDocument());
  });

  it("clears deeper selections when a different parent is chosen", async () => {
    const inst2 = { id: "i2", name: "Beta College", timezone: "UTC" };
    route({
      [`GET ${BASE}/institutes`]: () => json(200, [inst, inst2]),
      [`GET ${BASE}/departments?institute_id=i1`]: () => json(200, [dept]),
      [`GET ${BASE}/departments?institute_id=i2`]: () => json(200, []),
      [`GET ${BASE}/programs?department_id=d1`]: () => json(200, []),
    });
    renderPage();
    await userEvent.click(
      await screen.findByRole("button", { name: "Alpha College (Asia/Kolkata)" }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "CSE - Computer Science" }));
    expect(await screen.findByText("No programs yet.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Beta College (UTC)" }));
    expect(await screen.findByText("No departments yet.")).toBeInTheDocument();
    expect(screen.getByTestId("program-list")).toHaveTextContent(
      "Select a department to see its programs.",
    );
  });
});
