/** Types for the Teacher curriculum endpoints G1..G15 (FR-CUR-001..004). */

export type CurriculumStatus =
  "GENERATING" | "GENERATION_FAILED" | "DRAFT" | "ACTIVE" | "SUPERSEDED" | "RETURNED";

export type Classification = "CORE" | "OPTIONAL" | "SELF_STUDY";

export interface CurriculumVersion {
  id: string;
  subject_id: string;
  version_no: number;
  status: CurriculumStatus;
  origin: "AGENT" | "FLAT_FALLBACK";
  revision: number;
  validated_revision: number | null;
  validation_status: "NOT_RUN" | "PASSED" | "BLOCKED";
  failure_message: string | null;
  decision_reason: string | null;
}

export interface CurriculumUnit {
  id: string;
  order_index: number;
  name: string;
  weightage: number;
}

export interface CurriculumTopic {
  topic_id: string;
  name: string;
  unit_id: string | null;
  unit_weightage: number | null;
  outcomes: string[];
  bloom_level: string;
  est_hours: number;
  classification: Classification;
  order_index: number;
  source_chunk_ids: string[];
  is_orphan: boolean;
}

export interface CurriculumEdge {
  id: string;
  topic_id: string;
  prereq_topic_id: string;
  confidence: number;
  source: "AGENT" | "TEACHER";
  dropped: boolean;
  drop_reason: string | null;
  cross_subject: boolean;
  external_subject_code: string | null;
  external_topic_name: string | null;
}

export interface CurriculumFlag {
  id: string;
  kind: "CYCLE_EDGE_DROPPED" | "CYCLE_REMAINING" | "ORPHAN" | "DUPLICATE_TOPIC" | "SCOPE_VIOLATION";
  topic_id: string | null;
  other_topic_id: string | null;
  detail: Record<string, unknown> | null;
  blocking: boolean;
}

export interface CurriculumGraph {
  version: CurriculumVersion;
  units: CurriculumUnit[];
  topics: CurriculumTopic[];
  edges: CurriculumEdge[];
  flags: CurriculumFlag[];
  agent_run: { status: string; attempts: number; error: string | null } | null;
  threshold: { value: number; status: string } | null;
  embedding_config: { model_id: string; model_revision: string } | null;
  approval_blockers: string[];
  can_approve: boolean;
  is_owner: boolean;
  banner: string | null;
}
