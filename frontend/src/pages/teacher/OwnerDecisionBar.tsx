import { useState } from "react";

import {
  useActivateFallback,
  useApproveCurriculum,
  useRejectCurriculum,
} from "../../api/curriculumApi";
import { useNotify } from "../../hooks/useNotify";
import type { CurriculumGraph } from "../../types/curriculum";

interface Props {
  subjectId: string;
  graph: CurriculumGraph;
  hasActive: boolean;
}

/** FR-CUR-004: Approve / Reject / flat fallback. Rendered for the Subject Owner only; the server
 * rejects any other caller regardless. Approve is disabled with the reason while blocked. */
export default function OwnerDecisionBar({ subjectId, graph, hasActive }: Props) {
  const approve = useApproveCurriculum();
  const reject = useRejectCurriculum();
  const fallback = useActivateFallback();
  const notify = useNotify();
  const [reason, setReason] = useState("");
  if (!graph.is_owner) return null;
  const draft = graph.version.status === "DRAFT";
  const versionId = graph.version.id;
  return (
    <div className="space-x-1" data-testid="owner-decision-bar">
      <input
        aria-label="Decision reason"
        placeholder="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="border px-1"
      />
      {draft && (
        <>
          <button
            disabled={!graph.can_approve}
            title={graph.approval_blockers.join(" ")}
            className="rounded bg-green-700 px-2 text-white disabled:opacity-50"
            onClick={() =>
              approve.mutate(
                { versionId, reason },
                {
                  onSuccess: () => notify.success("Curriculum approved and activated."),
                  onError: notify.error,
                },
              )
            }
          >
            Approve and activate
          </button>
          <button
            className="rounded border px-2"
            onClick={() =>
              reject.mutate(
                { versionId, reason },
                {
                  onSuccess: () => notify.success("Curriculum returned to draft."),
                  onError: notify.error,
                },
              )
            }
          >
            Reject (return to draft)
          </button>
        </>
      )}
      {!hasActive && (
        <button
          className="rounded border px-2"
          onClick={() =>
            fallback.mutate(
              { subjectId, reason },
              {
                onSuccess: () => notify.success("Flat Unit order activated."),
                onError: notify.error,
              },
            )
          }
        >
          Activate flat Unit order
        </button>
      )}
    </div>
  );
}
