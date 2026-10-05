export type ContentType = "SYLLABUS" | "NOTES" | "PPT" | "PYQ" | "LAB";
export type VersionStatus = "DRAFT" | "ACTIVE" | "SUPERSEDED";
export type IngestionStatus = "PENDING" | "RUNNING" | "SUCCEEDED" | "FAILED";
export type StageName = "VALIDATE" | "EXTRACT" | "OCR" | "CLEAN" | "CHUNK" | "EMBED" | "STORE";
export type LinkStatus = "DRAFT" | "APPROVED" | "SUPERSEDED";

export interface UnitBrief {
  id: string;
  order_index: number;
  name: string;
  weightage: number;
}

export interface AssignedSubject {
  id: string;
  code: string;
  name: string;
  semester_no: number;
  is_owner: boolean;
  units: UnitBrief[];
}

export interface StageRun {
  stage: StageName;
  attempt: number;
  status: "RUNNING" | "SUCCEEDED" | "FAILED" | "SKIPPED";
  started_at: string;
  finished_at: string | null;
  detail: Record<string, unknown> | null;
  error: string | null;
}

export interface ContentVersion {
  id: string;
  content_asset_id: string;
  version_no: number;
  status: VersionStatus;
  ingestion_status: IngestionStatus;
  failed_stage: string | null;
  failure_message: string | null;
  unit_id: string | null;
  original_filename: string;
  ext: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
  ingestion_heartbeat_at?: string | null;
  /** Server-computed (finding M2): FAILED/PENDING now, or RUNNING with no activity past the timeout. */
  can_retry: boolean;
  /** When a RUNNING version becomes retryable if it stays stuck; null otherwise. */
  retry_available_at: string | null;
}

export interface ContentVersionDetail extends ContentVersion {
  content_type: ContentType;
  asset_title: string;
  subject_id: string;
  chunk_count: number;
  stage_runs: StageRun[];
}

export interface ContentAsset {
  id: string;
  subject_id: string;
  content_type: ContentType;
  title: string;
  versions: ContentVersion[];
}

export interface Chunk {
  id: string;
  content_version_id: string;
  unit_no: number | null;
  source_file: string;
  locator_type: string;
  locator: string;
  page_no: number | null;
  chunk_type: ContentType;
  chunk_index: number;
  text: string;
  token_count: number;
}

export interface ChunkReference {
  chunk: Chunk;
  content_version_id: string;
  version_no: number;
  version_status: VersionStatus;
  content_asset_id: string;
  source_file: string;
  locator: string;
}

export interface ResourceLink {
  id: string;
  subject_id: string;
  topic_label: string | null;
  unit_id: string | null;
  url: string;
  title: string;
  resource_type: string;
  est_minutes: number | null;
  status: LinkStatus;
  supersedes_link_id: string | null;
}

export interface ResourceLinkInput {
  url: string;
  title: string;
  resource_type: string;
  est_minutes?: number | null;
  topic_label?: string | null;
  unit_id?: string | null;
}
