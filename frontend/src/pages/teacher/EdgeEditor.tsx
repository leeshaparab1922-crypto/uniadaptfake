import { useState } from "react";

import { useAddEdge, useDeleteEdge } from "../../api/curriculumApi";
import { useNotify } from "../../hooks/useNotify";
import type { CurriculumGraph } from "../../types/curriculum";

/** FR-CUR-003: add / delete prerequisite edges. Dropped (cycle) edges are shown struck through. */
export default function EdgeEditor({ graph }: { graph: CurriculumGraph }) {
  const add = useAddEdge();
  const del = useDeleteEdge();
  const notify = useNotify();
  const [topicId, setTopicId] = useState("");
  const [prereqId, setPrereqId] = useState("");
  const [confidence, setConfidence] = useState("1");
  const editable = graph.version.status === "DRAFT" || graph.version.status === "RETURNED";
  const versionId = graph.version.id;
  const name = (
    id: string,
    e?: { external_topic_name: string | null; external_subject_code: string | null },
  ) =>
    graph.topics.find((t) => t.topic_id === id)?.name ??
    (e?.external_topic_name ? `${e.external_subject_code}: ${e.external_topic_name}` : "?");
  return (
    <section data-testid="edge-editor">
      <h3 className="font-semibold">Prerequisites</h3>
      <ul>
        {graph.edges.map((e) => (
          <li key={e.id}>
            {e.dropped ? <s>{label(e)}</s> : label(e)} ({e.confidence}, {e.source.toLowerCase()})
            {e.cross_subject && (
              <span className="ml-1 rounded bg-blue-100 px-1">{e.external_subject_code}</span>
            )}
            {editable && (
              <button
                className="ml-1"
                aria-label={`Delete edge ${name(e.topic_id)} requires ${name(e.prereq_topic_id, e)}`}
                onClick={() => del.mutate({ versionId, edgeId: e.id }, { onError: notify.error })}
              >
                Delete
              </button>
            )}
          </li>
        ))}
      </ul>
      {editable && (
        <form
          onSubmit={(ev) => {
            ev.preventDefault();
            add.mutate(
              { versionId, topicId, prereqTopicId: prereqId, confidence: Number(confidence) },
              { onSuccess: () => notify.success("Edge added."), onError: notify.error },
            );
          }}
        >
          <select aria-label="Topic" value={topicId} onChange={(e) => setTopicId(e.target.value)}>
            <option value="">Topic...</option>
            {graph.topics.map((t) => (
              <option key={t.topic_id} value={t.topic_id}>
                {t.name}
              </option>
            ))}
          </select>
          {" requires "}
          <select
            aria-label="Prerequisite"
            value={prereqId}
            onChange={(e) => setPrereqId(e.target.value)}
          >
            <option value="">Prerequisite...</option>
            {graph.topics.map((t) => (
              <option key={t.topic_id} value={t.topic_id}>
                {t.name}
              </option>
            ))}
          </select>
          <input
            aria-label="Confidence"
            type="number"
            min="0"
            max="1"
            step="0.1"
            value={confidence}
            onChange={(e) => setConfidence(e.target.value)}
            className="w-16 border px-1"
          />
          <button type="submit" disabled={!topicId || !prereqId || topicId === prereqId}>
            Add prerequisite
          </button>
        </form>
      )}
    </section>
  );

  function label(e: CurriculumGraph["edges"][number]) {
    return `${name(e.topic_id)} requires ${name(e.prereq_topic_id, e)}`;
  }
}
