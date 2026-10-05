import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ContentUploadForm from "../pages/teacher/ContentUploadForm";
import IngestionStatus from "../pages/teacher/IngestionStatus";
import type { AssignedSubject, ContentVersionDetail } from "../types/content";

const m = vi.hoisted(() => ({ upload: vi.fn(), detail: vi.fn(), retry: vi.fn() }));

vi.mock("../api/contentApi", () => ({
  MAX_UPLOAD_BYTES: 25 * 1024 * 1024,
  ALLOWED_EXTENSIONS: ["pdf", "pptx", "docx", "txt"],
  useUpload: () => ({ mutate: m.upload, isPending: false }),
  useVersionDetail: () => m.detail(),
  useRetryIngestion: () => ({ mutate: m.retry, isPending: false }),
}));
vi.mock("../hooks/useNotify", () => ({ useNotify: () => ({ success: vi.fn(), error: vi.fn() }) }));

const subject: AssignedSubject = {
  id: "s1",
  code: "CS301",
  name: "Data Structures",
  semester_no: 3,
  is_owner: false,
  units: [{ id: "u1", order_index: 1, name: "Basics", weightage: 100 }],
};

beforeEach(() => vi.clearAllMocks());

async function fillFileAndTitle() {
  await userEvent.upload(
    screen.getByLabelText("File"),
    new File(["hello"], "n.txt", { type: "text/plain" }),
  );
  await userEvent.type(screen.getByLabelText("Title"), "Notes");
}

describe("Upload Unit choice (finding m2)", () => {
  it("blocks a non-syllabus upload until a Unit or All units is chosen", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    await fillFileAndTitle();
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/choose the unit/i);
    expect(m.upload).not.toHaveBeenCalled();
  });

  it("sends All units explicitly", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    await fillFileAndTitle();
    await userEvent.selectOptions(screen.getByLabelText("Unit"), "__all__");
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(m.upload.mock.calls[0][0]).toMatchObject({ unitId: undefined, allUnits: true });
  });

  it("does not ask a syllabus for a Unit", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    await userEvent.selectOptions(screen.getByLabelText("Content type"), "SYLLABUS");
    expect(screen.queryByLabelText("Unit")).not.toBeInTheDocument();
    expect(screen.getByText(/a syllabus covers all units/i)).toBeInTheDocument();
    await fillFileAndTitle();
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(m.upload.mock.calls[0][0]).toMatchObject({
      contentType: "SYLLABUS",
      unitId: undefined,
      allUnits: false,
    });
  });
});

function detail(over: Partial<ContentVersionDetail>) {
  const data: ContentVersionDetail = {
    id: "v1",
    content_asset_id: "a1",
    version_no: 1,
    status: "DRAFT",
    ingestion_status: "RUNNING",
    failed_stage: null,
    failure_message: null,
    unit_id: null,
    original_filename: "n.pdf",
    ext: "pdf",
    mime_type: "application/pdf",
    size_bytes: 10,
    sha256: "x",
    created_at: "2026-01-01",
    can_retry: false,
    retry_available_at: null,
    content_type: "NOTES",
    asset_title: "Notes",
    subject_id: "s1",
    chunk_count: 0,
    stage_runs: [],
    ...over,
  };
  m.detail.mockReturnValue({ isLoading: false, isError: false, data });
}

describe("Retry for stuck ingestion (finding M2)", () => {
  it("hides Retry while a running job is still active and says when it becomes available", () => {
    detail({ retry_available_at: "2026-10-04T12:40:00Z" });
    render(<IngestionStatus versionId="v1" />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
    expect(screen.getByTestId("stuck-hint")).toHaveTextContent(/retry becomes available/i);
  });

  it("offers Retry for a running job that stopped responding", async () => {
    detail({ can_retry: true, retry_available_at: "2026-10-04T10:00:00Z" });
    render(<IngestionStatus versionId="v1" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/stopped responding/i);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(m.retry).toHaveBeenCalledWith("v1", expect.anything());
  });

  it("offers Retry for a version still waiting in the queue", async () => {
    detail({ ingestion_status: "PENDING", can_retry: true });
    render(<IngestionStatus versionId="v1" />);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(m.retry).toHaveBeenCalledTimes(1);
  });

  it("never offers Retry for a succeeded version", () => {
    detail({ ingestion_status: "SUCCEEDED", can_retry: false });
    render(<IngestionStatus versionId="v1" />);
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});
