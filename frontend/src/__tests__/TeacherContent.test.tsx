import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ChunkViewer from "../pages/teacher/ChunkViewer";
import ContentUploadForm from "../pages/teacher/ContentUploadForm";
import IngestionStatus from "../pages/teacher/IngestionStatus";
import OwnerActions from "../pages/teacher/OwnerActions";
import ResourceLinks from "../pages/teacher/ResourceLinks";
import TeacherSubjects from "../pages/teacher/TeacherSubjects";
import type { AssignedSubject, ContentAsset, ContentVersion } from "../types/content";

const m = vi.hoisted(() => ({
  subjects: vi.fn(),
  upload: vi.fn(),
  detail: vi.fn(),
  retry: vi.fn(),
  chunks: vi.fn(),
  ref: vi.fn(),
  links: vi.fn(),
  register: vi.fn(),
  approve: vi.fn(),
  activate: vi.fn(),
  rollback: vi.fn(),
  notifyError: vi.fn(),
}));

vi.mock("../api/contentApi", () => ({
  MAX_UPLOAD_BYTES: 25 * 1024 * 1024,
  ALLOWED_EXTENSIONS: ["pdf", "pptx", "docx", "txt"],
  useMySubjects: () => m.subjects(),
  useUpload: () => ({ mutate: m.upload, isPending: false }),
  useVersionDetail: () => m.detail(),
  useRetryIngestion: () => ({ mutate: m.retry }),
  useChunks: () => m.chunks(),
  useChunkReference: () => m.ref(),
  useLinks: () => m.links(),
  useRegisterLink: () => ({ mutate: m.register }),
  useReviseLink: () => ({ mutate: vi.fn() }),
  useApproveLink: () => ({ mutate: m.approve }),
  useActivateVersion: () => ({ mutate: m.activate }),
  useRollback: () => ({ mutate: m.rollback }),
}));
vi.mock("../hooks/useNotify", () => ({
  useNotify: () => ({ success: vi.fn(), error: m.notifyError }),
}));

const subject: AssignedSubject = {
  id: "s1",
  code: "CS301",
  name: "Data Structures",
  semester_no: 3,
  is_owner: false,
  units: [{ id: "u1", order_index: 1, name: "Basics", weightage: 100 }],
};
const version = (over: Partial<ContentVersion> = {}): ContentVersion => ({
  id: "v1",
  content_asset_id: "a1",
  version_no: 1,
  status: "DRAFT",
  ingestion_status: "SUCCEEDED",
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
  ...over,
});
const asset: ContentAsset = {
  id: "a1",
  subject_id: "s1",
  content_type: "NOTES",
  title: "Notes",
  versions: [version()],
};

beforeEach(() => vi.clearAllMocks());

describe("TeacherSubjects (C1)", () => {
  it("lists only assigned subjects and shows the Owner badge", () => {
    m.subjects.mockReturnValue({
      data: [
        { ...subject, is_owner: true },
        { ...subject, id: "s2", is_owner: false },
      ],
      isLoading: false,
      isError: false,
    });
    render(<TeacherSubjects selectedId={null} onSelect={vi.fn()} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByTestId("owner-badge-s1")).toBeInTheDocument();
    expect(screen.queryByTestId("owner-badge-s2")).not.toBeInTheDocument();
  });
  it("shows an empty state when unassigned", () => {
    m.subjects.mockReturnValue({ data: [], isLoading: false, isError: false });
    render(<TeacherSubjects selectedId={null} onSelect={vi.fn()} />);
    expect(screen.getByText(/not assigned to any subject/i)).toBeInTheDocument();
  });
});

describe("ContentUploadForm (FR-CON-001)", () => {
  it("blocks a disallowed extension client-side", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    await userEvent.upload(screen.getByLabelText("File"), new File(["x"], "old.doc"), {
      applyAccept: false,
    });
    await userEvent.type(screen.getByLabelText("Title"), "T");
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/allowed types/i);
    expect(m.upload).not.toHaveBeenCalled();
  });
  it("blocks files over 25 MB", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    const big = new File(["x"], "big.pdf");
    Object.defineProperty(big, "size", { value: 26 * 1024 * 1024 });
    await userEvent.upload(screen.getByLabelText("File"), big);
    await userEvent.type(screen.getByLabelText("Title"), "T");
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/25 MB/);
  });
  it("submits a valid file", async () => {
    render(<ContentUploadForm subject={subject} assets={[]} />);
    await userEvent.upload(
      screen.getByLabelText("File"),
      new File(["hello"], "n.txt", { type: "text/plain" }),
    );
    await userEvent.type(screen.getByLabelText("Title"), "Notes");
    await userEvent.selectOptions(screen.getByLabelText("Unit"), "u1");
    await userEvent.click(screen.getByRole("button", { name: /upload/i }));
    expect(m.upload).toHaveBeenCalledTimes(1);
    expect(m.upload.mock.calls[0][0]).toMatchObject({
      subjectId: "s1",
      contentType: "NOTES",
      title: "Notes",
      unitId: "u1",
      allUnits: false,
    });
  });
});

describe("IngestionStatus (FR-CON-002 status display)", () => {
  it("renders a failed stage with the clear message and a Retry button", async () => {
    m.detail.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        ...version({
          ingestion_status: "FAILED",
          can_retry: true,
          failed_stage: "OCR",
          failure_message:
            "OCR could not read page(s) 2. Text could not be extracted from this content. Upload a clearer file or enter a reference.",
        }),
        content_type: "NOTES",
        asset_title: "Notes",
        subject_id: "s1",
        chunk_count: 0,
        stage_runs: [
          {
            stage: "VALIDATE",
            attempt: 1,
            status: "SUCCEEDED",
            started_at: "",
            finished_at: "",
            detail: null,
            error: null,
          },
          {
            stage: "OCR",
            attempt: 1,
            status: "FAILED",
            started_at: "",
            finished_at: "",
            detail: null,
            error: "x",
          },
        ],
      },
    });
    render(<IngestionStatus versionId="v1" />);
    expect(screen.getByRole("alert")).toHaveTextContent(/failed at OCR/i);
    expect(screen.getByRole("alert")).toHaveTextContent(/upload a clearer file/i);
    await userEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(m.retry).toHaveBeenCalledWith("v1", expect.anything());
  });
  it("shows queued state when no stage has run", () => {
    m.detail.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        ...version({ ingestion_status: "PENDING" }),
        content_type: "NOTES",
        asset_title: "N",
        subject_id: "s1",
        chunk_count: 0,
        stage_runs: [],
      },
    });
    render(<IngestionStatus versionId="v1" />);
    expect(screen.getByText(/queued/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});

describe("OwnerActions (FR-CON-004)", () => {
  it("is hidden for a non-Owner (CO) teacher", () => {
    render(<OwnerActions isOwner={false} asset={asset} version={version()} />);
    expect(screen.queryByTestId("owner-actions")).not.toBeInTheDocument();
  });
  it("shows Activate for an Owner on an ingested DRAFT and calls the API", async () => {
    render(<OwnerActions isOwner asset={asset} version={version()} />);
    await userEvent.click(screen.getByRole("button", { name: /activate/i }));
    expect(m.activate).toHaveBeenCalledWith({ versionId: "v1", reason: "" }, expect.anything());
  });
  it("hides Activate when ingestion has not succeeded; offers rollback only for SUPERSEDED", () => {
    const { rerender } = render(
      <OwnerActions isOwner asset={asset} version={version({ ingestion_status: "FAILED" })} />,
    );
    expect(screen.queryByTestId("owner-actions")).not.toBeInTheDocument();
    rerender(<OwnerActions isOwner asset={asset} version={version({ status: "SUPERSEDED" })} />);
    expect(screen.getByRole("button", { name: /roll back/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^activate$/i })).not.toBeInTheDocument();
  });
});

describe("ResourceLinks (FR-CON-001/004)", () => {
  beforeEach(() =>
    m.links.mockReturnValue({
      data: [
        {
          id: "l1",
          subject_id: "s1",
          topic_label: null,
          unit_id: null,
          url: "https://e.com",
          title: "E",
          resource_type: "OTHER",
          est_minutes: null,
          status: "DRAFT",
          supersedes_link_id: null,
        },
      ],
    }),
  );
  it("rejects non-HTTPS links before calling the API", async () => {
    render(<ResourceLinks subjectId="s1" isOwner={false} />);
    await userEvent.type(screen.getByLabelText("Link URL"), "http://example.com");
    await userEvent.type(screen.getByLabelText("Link title"), "T");
    await userEvent.click(screen.getByRole("button", { name: /add link/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/https/i);
    expect(m.register).not.toHaveBeenCalled();
  });
  it("shows Approve only to the Owner", () => {
    const { rerender } = render(<ResourceLinks subjectId="s1" isOwner={false} />);
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    rerender(<ResourceLinks subjectId="s1" isOwner />);
    expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
  });
});

describe("ChunkViewer (FR-CON-003)", () => {
  it("shows unit/locator metadata and resolves a citation", async () => {
    m.chunks.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        {
          id: "c1",
          content_version_id: "v1",
          unit_no: 2,
          source_file: "n.pdf",
          locator_type: "PAGE",
          locator: "page:7",
          page_no: 7,
          chunk_type: "NOTES",
          chunk_index: 0,
          text: "t",
          token_count: 10,
        },
      ],
    });
    m.ref.mockReturnValue({
      data: {
        chunk: {},
        content_version_id: "v1",
        version_no: 1,
        version_status: "SUPERSEDED",
        content_asset_id: "a1",
        source_file: "n.pdf",
        locator: "page:7",
      },
    });
    render(<ChunkViewer versionId="v1" />);
    expect(screen.getByText("page:7")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /resolve citation/i }));
    expect(screen.getByTestId("citation")).toHaveTextContent(/SUPERSEDED.*n\.pdf.*page:7/);
  });
});
