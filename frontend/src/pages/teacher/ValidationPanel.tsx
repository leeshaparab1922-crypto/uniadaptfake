import type { CurriculumGraph } from "../../types/curriculum";

/** FR-CUR-002: shows the Section 37 cycle banner, flagged edges, orphans, duplicate pairs, the
 * embedding model / threshold in force and why approval is currently blocked. */
export default function ValidationPanel({ graph }: { graph: CurriculumGraph }) {
  const name = (id: string | null) =>
    graph.topics.find((t) => t.topic_id === id)?.name ?? "removed Topic";
  const duplicates = graph.flags.filter((f) => f.kind === "DUPLICATE_TOPIC");
  const orphans = graph.flags.filter((f) => f.kind === "ORPHAN");
  return (
    <section className="rounded border p-2" data-testid="validation-panel">
      <h3 className="font-semibold">Validation</h3>
      {graph.banner && (
        <p role="alert" className="rounded bg-yellow-100 p-1">
          {graph.banner}
        </p>
      )}
      <p>
        Status: {graph.version.validation_status} (revision {graph.version.revision}, validated{" "}
        {graph.version.validated_revision ?? "never"})
      </p>
      {graph.embedding_config && (
        <p>
          Embedding model {graph.embedding_config.model_id}@
          {graph.embedding_config.model_revision.slice(0, 8)}; duplicate threshold{" "}
          {graph.threshold ? `${graph.threshold.value} (${graph.threshold.status})` : "not set"}
        </p>
      )}
      <ul>
        {graph.edges
          .filter((e) => e.dropped)
          .map((e) => (
            <li key={e.id} className="line-through-parent">
              <s>
                {name(e.topic_id)} requires {name(e.prereq_topic_id)} ({e.confidence})
              </s>{" "}
              {e.drop_reason}
            </li>
          ))}
        {orphans.map((f) => (
          <li key={f.id}>Orphan: {name(f.topic_id)} has no Unit.</li>
        ))}
        {duplicates.map((f) => (
          <li key={f.id}>
            Possible duplicate: {name(f.topic_id)} / {name(f.other_topic_id)} (similarity{" "}
            {String(f.detail?.similarity)})
          </li>
        ))}
      </ul>
      {graph.approval_blockers.length > 0 && (
        <ul data-testid="approval-blockers" className="text-red-700">
          {graph.approval_blockers.map((b) => (
            <li key={b}>{b}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
