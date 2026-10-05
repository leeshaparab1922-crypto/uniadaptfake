import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CurriculumPage from "../pages/teacher/CurriculumPage";
import EdgeEditor from "../pages/teacher/EdgeEditor";
import OwnerDecisionBar from "../pages/teacher/OwnerDecisionBar";
import TopicEditor from "../pages/teacher/TopicEditor";
import ValidationPanel from "../pages/teacher/ValidationPanel";
import type { AssignedSubject } from "../types/content";
import type { CurriculumGraph } from "../types/curriculum";

const m = vi.hoisted(() => ({
  versions: vi.fn(),
  graph: vi.fn(),
  generate: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  fallback: vi.fn(),
  edit: vi.fn(),
  addEdge: vi.fn(),
  delEdge: vi.fn(),
  reorder: vi.fn(),
}));

vi.mock("../api/curriculumApi", () => ({
  useCurriculumVersions: () => m.versions(),
  useCurriculumGraph: () => m.graph(),
  useGenerateCurriculum: () => ({ mutate: m.generate, isPending: false }),
  useApproveCurriculum: () => ({ mutate: m.approve }),
  useRejectCurriculum: () => ({ mutate: m.reject }),
  useActivateFallback: () => ({ mutate: m.fallback }),
  useEditTopic: () => ({ mutate: m.edit }),
  useDeleteTopic: () => ({ mutate: vi.fn() }),
  useReorder: () => ({ mutate: m.reorder }),
  useMerge: () => ({ mutate: vi.fn() }),
  useSplit: () => ({ mutate: vi.fn() }),
  useAddEdge: () => ({ mutate: m.addEdge }),
  useDeleteEdge: () => ({ mutate: m.delEdge }),
  useRevalidate: () => ({ mutate: vi.fn() }),
}));
vi.mock("../hooks/useNotify", () => ({ useNotify: () => ({ success: vi.fn(), error: vi.fn() }) }));

const subject: AssignedSubject = {
  id: "s1",
  code: "CS301",
  name: "Data Structures",
  semester_no: 3,
  is_owner: false,
  units: [],
};

function graph(over: Partial<CurriculumGraph> = {}): CurriculumGraph {
  return {
    version: {
      id: "c1",
      subject_id: "s1",
      version_no: 1,
      status: "DRAFT",
      origin: "AGENT",
      revision: 2,
      validated_revision: 2,
      validation_status: "PASSED",
      failure_message: null,
      decision_reason: null,
    },
    units: [{ id: "u1", order_index: 1, name: "Basics", weightage: 40 }],
    topics: [
      {
        topic_id: "a",
        name: "Arrays",
        unit_id: "u1",
        unit_weightage: 40,
        outcomes: ["x"],
        bloom_level: "APPLY",
        est_hours: 3,
        classification: "CORE",
        order_index: 1,
        source_chunk_ids: [],
        is_orphan: false,
      },
      {
        topic_id: "b",
        name: "Lists",
        unit_id: "u1",
        unit_weightage: 40,
        outcomes: ["y"],
        bloom_level: "APPLY",
        est_hours: 2,
        classification: "CORE",
        order_index: 2,
        source_chunk_ids: [],
        is_orphan: false,
      },
    ],
    edges: [
      {
        id: "e1",
        topic_id: "a",
        prereq_topic_id: "b",
        confidence: 0.8,
        source: "AGENT",
        dropped: false,
        drop_reason: null,
        cross_subject: false,
        external_subject_code: null,
        external_topic_name: null,
      },
      {
        id: "e2",
        topic_id: "b",
        prereq_topic_id: "a",
        confidence: 0.4,
        source: "AGENT",
        dropped: true,
        drop_reason: "Dropped lowest-confidence edge",
        cross_subject: false,
        external_subject_code: null,
        external_topic_name: null,
      },
    ],
    flags: [],
    agent_run: null,
    threshold: { value: 0.92, status: "ACTIVE" },
    embedding_config: {
      model_id: "BAAI/bge-m3",
      model_revision: "5617a9f61b028005a4858fdac845db406aefb181",
    },
    approval_blockers: [],
    can_approve: true,
    is_owner: true,
    banner: "A prerequisite cycle was detected. Review the flagged relationship.",
    ...over,
  };
}

beforeEach(() => {
  Object.values(m).forEach((f) => f.mockReset());
  m.versions.mockReturnValue({ data: [], isLoading: false, isError: false });
  m.graph.mockReturnValue({ data: undefined });
});

describe("curriculum UI", () => {
  it("shows the Section 37 cycle banner, the dropped edge struck through, and the model/threshold", () => {
    render(<ValidationPanel graph={graph()} />);
    expect(screen.getByRole("alert")).toHaveTextContent("A prerequisite cycle was detected");
    expect(screen.getByText(/Lists requires Arrays \(0.4\)/).tagName).toBe("S");
    expect(screen.getByText(/BAAI\/bge-m3@5617a9f6/)).toHaveTextContent("0.92 (ACTIVE)");
  });

  it("lists approval blockers", () => {
    render(
      <ValidationPanel
        graph={graph({ approval_blockers: ["threshold not validated"], can_approve: false })}
      />,
    );
    expect(screen.getByTestId("approval-blockers")).toHaveTextContent("threshold not validated");
  });

  it("hides decision controls from a CO teacher", () => {
    render(<OwnerDecisionBar subjectId="s1" hasActive graph={graph({ is_owner: false })} />);
    expect(screen.queryByTestId("owner-decision-bar")).toBeNull();
  });

  it("lets the Owner approve with a reason, and disables approve while blocked", async () => {
    const { rerender } = render(<OwnerDecisionBar subjectId="s1" hasActive graph={graph()} />);
    await userEvent.type(screen.getByLabelText("Decision reason"), "looks right");
    await userEvent.click(screen.getByRole("button", { name: "Approve and activate" }));
    expect(m.approve).toHaveBeenCalledWith(
      { versionId: "c1", reason: "looks right" },
      expect.anything(),
    );
    rerender(
      <OwnerDecisionBar
        subjectId="s1"
        hasActive
        graph={graph({ can_approve: false, approval_blockers: ["x"] })}
      />,
    );
    expect(screen.getByRole("button", { name: "Approve and activate" })).toBeDisabled();
  });

  it("offers the flat Unit-order fallback only when no ACTIVE curriculum exists", async () => {
    const { rerender } = render(<OwnerDecisionBar subjectId="s1" hasActive graph={graph()} />);
    expect(screen.queryByRole("button", { name: "Activate flat Unit order" })).toBeNull();
    rerender(<OwnerDecisionBar subjectId="s1" hasActive={false} graph={graph()} />);
    await userEvent.click(screen.getByRole("button", { name: "Activate flat Unit order" }));
    expect(m.fallback).toHaveBeenCalled();
  });

  it("lets any assigned teacher edit a DRAFT but not an ACTIVE version", async () => {
    const { rerender } = render(<TopicEditor graph={graph({ is_owner: false })} />);
    await userEvent.selectOptions(screen.getByLabelText("Classification of Arrays"), "OPTIONAL");
    expect(m.edit).toHaveBeenCalledWith(
      { versionId: "c1", topicId: "a", changes: { classification: "OPTIONAL" } },
      expect.anything(),
    );
    await userEvent.click(screen.getByRole("button", { name: "Move Arrays down" }));
    expect(m.reorder).toHaveBeenCalledWith(
      { versionId: "c1", unitId: "u1", topicIds: ["b", "a"] },
      expect.anything(),
    );
    const active = graph();
    active.version.status = "ACTIVE";
    rerender(<TopicEditor graph={active} />);
    expect(screen.getByLabelText("Name of Arrays")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Remove Arrays" })).toBeNull();
  });

  it("adds and deletes prerequisite edges", async () => {
    render(<EdgeEditor graph={graph()} />);
    await userEvent.selectOptions(screen.getByLabelText("Topic"), "a");
    await userEvent.selectOptions(screen.getByLabelText("Prerequisite"), "b");
    await userEvent.click(screen.getByRole("button", { name: "Add prerequisite" }));
    expect(m.addEdge).toHaveBeenCalledWith(
      { versionId: "c1", topicId: "a", prereqTopicId: "b", confidence: 1 },
      expect.anything(),
    );
    await userEvent.click(screen.getAllByRole("button", { name: /Delete edge/ })[0]);
    expect(m.delEdge).toHaveBeenCalled();
  });

  it("requests generation and shows version statuses", async () => {
    m.versions.mockReturnValue({
      data: [
        { id: "c1", version_no: 1, status: "GENERATING", origin: "AGENT", failure_message: null },
      ],
      isLoading: false,
      isError: false,
    });
    render(<CurriculumPage subject={subject} />);
    expect(screen.getByTestId("cv-status-c1")).toHaveTextContent("GENERATING");
    expect(screen.getByText(/Queued, will retry/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Generate curriculum" }));
    expect(m.generate).toHaveBeenCalledWith("s1", expect.anything());
  });
});
