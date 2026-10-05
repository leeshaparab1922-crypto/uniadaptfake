import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ResourceLinks from "../pages/teacher/ResourceLinks";
import type { ResourceLink } from "../types/content";

const m = vi.hoisted(() => ({ links: vi.fn(), register: vi.fn(), revise: vi.fn(), approve: vi.fn() }));

vi.mock("../api/contentApi", () => ({
  useLinks: () => m.links(),
  useRegisterLink: () => ({ mutate: m.register }),
  useReviseLink: () => ({ mutate: m.revise }),
  useApproveLink: () => ({ mutate: m.approve }),
}));
vi.mock("../hooks/useNotify", () => ({ useNotify: () => ({ success: vi.fn(), error: vi.fn() }) }));

const units = [{ id: "u1", order_index: 1, name: "Basics", weightage: 100 }];
const link = (over: Partial<ResourceLink>): ResourceLink => ({
  id: "l1",
  subject_id: "s1",
  topic_label: "BST",
  unit_id: "u1",
  url: "https://e.com/trees",
  title: "Trees",
  resource_type: "VIDEO",
  est_minutes: 20,
  status: "APPROVED",
  supersedes_link_id: null,
  ...over,
});

beforeEach(() => vi.clearAllMocks());

describe("ResourceLinks fixes (finding N5)", () => {
  it("offers Revise only for the approved link", () => {
    m.links.mockReturnValue({
      data: [
        link({ id: "a", status: "APPROVED" }),
        link({ id: "d", status: "DRAFT", title: "Draft" }),
        link({ id: "s", status: "SUPERSEDED", title: "Old" }),
      ],
    });
    render(<ResourceLinks subjectId="s1" isOwner={false} units={units} />);
    expect(screen.getAllByRole("button", { name: /revise/i })).toHaveLength(1);
  });

  it("sends the edited values when a revision is saved", async () => {
    m.links.mockReturnValue({ data: [link({})] });
    render(<ResourceLinks subjectId="s1" isOwner={false} units={units} />);
    await userEvent.click(screen.getByRole("button", { name: /revise/i }));
    const form = screen.getByTestId("revise-form");
    const title = within(form).getByLabelText("Revised title");
    expect(title).toHaveValue("Trees");
    await userEvent.clear(title);
    await userEvent.type(title, "Trees, revised");
    await userEvent.click(within(form).getByRole("button", { name: /save revision/i }));
    expect(m.revise).toHaveBeenCalledTimes(1);
    expect(m.revise.mock.calls[0][0]).toEqual({
      linkId: "l1",
      input: {
        url: "https://e.com/trees",
        title: "Trees, revised",
        resource_type: "VIDEO",
        unit_id: "u1",
        topic_label: "BST",
        est_minutes: 20,
      },
    });
  });

  it("registers a link with Unit, topic, type and minutes", async () => {
    m.links.mockReturnValue({ data: [] });
    render(<ResourceLinks subjectId="s1" isOwner={false} units={units} />);
    await userEvent.type(screen.getByLabelText("Link URL"), "https://e.com/x");
    await userEvent.type(screen.getByLabelText("Link title"), "X");
    await userEvent.selectOptions(screen.getByLabelText("Link type"), "ARTICLE");
    await userEvent.selectOptions(screen.getByLabelText("Link Unit"), "u1");
    await userEvent.type(screen.getByLabelText("Link topic"), "Arrays");
    await userEvent.type(screen.getByLabelText("Link minutes"), "15");
    await userEvent.click(screen.getByRole("button", { name: /add link/i }));
    expect(m.register.mock.calls[0][0]).toEqual({
      subjectId: "s1",
      input: {
        url: "https://e.com/x",
        title: "X",
        resource_type: "ARTICLE",
        unit_id: "u1",
        topic_label: "Arrays",
        est_minutes: 15,
      },
    });
  });

  it("rejects non-positive minutes before calling the API", async () => {
    m.links.mockReturnValue({ data: [] });
    render(<ResourceLinks subjectId="s1" isOwner={false} units={units} />);
    await userEvent.type(screen.getByLabelText("Link URL"), "https://e.com/x");
    await userEvent.type(screen.getByLabelText("Link title"), "X");
    await userEvent.type(screen.getByLabelText("Link minutes"), "0");
    await userEvent.click(screen.getByRole("button", { name: /add link/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/positive whole number/i);
    expect(m.register).not.toHaveBeenCalled();
  });
});
