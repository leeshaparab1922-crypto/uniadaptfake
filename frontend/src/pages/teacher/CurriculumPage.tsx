import { useState } from "react";

import {
  useCurriculumGraph,
  useCurriculumVersions,
  useGenerateCurriculum,
} from "../../api/curriculumApi";
import { useNotify } from "../../hooks/useNotify";
import type { AssignedSubject } from "../../types/content";
import EdgeEditor from "./EdgeEditor";
import MergeSplitDialogs from "./MergeSplitDialogs";
import OwnerDecisionBar from "./OwnerDecisionBar";
import TopicEditor from "./TopicEditor";
import ValidationPanel from "./ValidationPanel";

/** Curriculum tab for one Subject (FR-CUR-001..004): version chain, generate, review/edit, Owner decision. */
export default function CurriculumPage({ subject }: { subject: AssignedSubject }) {
  const { data: versions, isLoading, isError } = useCurriculumVersions(subject.id);
  const generate = useGenerateCurriculum();
  const notify = useNotify();
  const [selected, setSelected] = useState<string | null>(null);
  const current = selected ?? versions?.[0]?.id ?? null;
  const { data: graph } = useCurriculumGraph(current);

  if (isLoading) return <p className="p-4 text-sm">Loading curriculum...</p>;
  if (isError)
    return (
      <p role="alert" className="p-4 text-sm">
        Could not load the curriculum.
      </p>
    );
  const hasActive = (versions ?? []).some((v) => v.status === "ACTIVE");

  return (
    <div className="space-y-3 p-4 text-sm" data-testid="curriculum-page">
      <h1 className="text-lg font-semibold">{subject.code} curriculum</h1>
      <button
        className="rounded bg-blue-700 px-2 py-1 text-white"
        disabled={generate.isPending}
        onClick={() =>
          generate.mutate(subject.id, {
            onSuccess: (v) => {
              setSelected(v.id);
              notify.success("Generation requested.");
            },
            onError: notify.error,
          })
        }
      >
        Generate curriculum
      </button>
      <ul data-testid="curriculum-versions">
        {(versions ?? []).map((v) => (
          <li key={v.id}>
            <button className="underline" onClick={() => setSelected(v.id)}>
              v{v.version_no}
            </button>{" "}
            <span className="rounded bg-gray-100 px-1" data-testid={`cv-status-${v.id}`}>
              {v.status}
            </span>{" "}
            {v.status === "GENERATING" && (
              <span>Queued, will retry if the AI provider is unavailable.</span>
            )}
            {v.status === "GENERATION_FAILED" && (
              <span className="text-red-700">{v.failure_message}</span>
            )}
            {v.origin === "FLAT_FALLBACK" && <span> (flat Unit order)</span>}
          </li>
        ))}
        {(versions ?? []).length === 0 && <li>No curriculum yet.</li>}
      </ul>
      {!hasActive && subject.is_owner && !graph && <OwnerFallbackOnly subjectId={subject.id} />}
      {graph && (
        <div className="space-y-3">
          <ValidationPanel graph={graph} />
          <TopicEditor graph={graph} />
          <EdgeEditor graph={graph} />
          <MergeSplitDialogs graph={graph} />
          <OwnerDecisionBar subjectId={subject.id} graph={graph} hasActive={hasActive} />
        </div>
      )}
    </div>
  );
}

/** With no version at all the Owner can still activate the flat Unit-order fallback (ASM-004). */
function OwnerFallbackOnly({ subjectId }: { subjectId: string }) {
  return (
    <OwnerDecisionBar
      subjectId={subjectId}
      hasActive={false}
      graph={{
        version: {
          id: "",
          subject_id: subjectId,
          version_no: 0,
          status: "RETURNED",
          origin: "AGENT",
          revision: 1,
          validated_revision: null,
          validation_status: "NOT_RUN",
          failure_message: null,
          decision_reason: null,
        },
        units: [],
        topics: [],
        edges: [],
        flags: [],
        agent_run: null,
        threshold: null,
        embedding_config: null,
        approval_blockers: [],
        can_approve: false,
        is_owner: true,
        banner: null,
      }}
    />
  );
}
