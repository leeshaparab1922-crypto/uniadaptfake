import { useState } from "react";

import { useMerge, useSplit } from "../../api/curriculumApi";
import { useNotify } from "../../hooks/useNotify";
import type { CurriculumGraph } from "../../types/curriculum";

/** FR-CUR-003: merge several Topics into one (lineage kept) or split one Topic into named parts. */
export default function MergeSplitDialogs({ graph }: { graph: CurriculumGraph }) {
  const merge = useMerge();
  const split = useSplit();
  const notify = useNotify();
  const [picked, setPicked] = useState<string[]>([]);
  const [target, setTarget] = useState("");
  const [splitId, setSplitId] = useState("");
  const [parts, setParts] = useState("");
  const editable = graph.version.status === "DRAFT" || graph.version.status === "RETURNED";
  if (!editable) return null;
  const versionId = graph.version.id;
  const names = parts
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
  return (
    <section data-testid="merge-split">
      <fieldset>
        <legend className="font-semibold">Merge Topics</legend>
        {graph.topics.map((t) => (
          <label key={t.topic_id} className="mr-2">
            <input
              type="checkbox"
              aria-label={`Merge ${t.name}`}
              checked={picked.includes(t.topic_id)}
              onChange={(e) =>
                setPicked(
                  e.target.checked
                    ? [...picked, t.topic_id]
                    : picked.filter((p) => p !== t.topic_id),
                )
              }
            />
            {t.name}
          </label>
        ))}
        <select aria-label="Keep Topic" value={target} onChange={(e) => setTarget(e.target.value)}>
          <option value="">Keep...</option>
          {picked.map((id) => (
            <option key={id} value={id}>
              {graph.topics.find((t) => t.topic_id === id)?.name}
            </option>
          ))}
        </select>
        <button
          disabled={picked.length < 2 || !picked.includes(target)}
          onClick={() =>
            merge.mutate(
              { versionId, topicIds: picked, targetTopicId: target },
              { onSuccess: () => setPicked([]), onError: notify.error },
            )
          }
        >
          Merge
        </button>
      </fieldset>
      <fieldset>
        <legend className="font-semibold">Split a Topic</legend>
        <select
          aria-label="Topic to split"
          value={splitId}
          onChange={(e) => setSplitId(e.target.value)}
        >
          <option value="">Topic...</option>
          {graph.topics.map((t) => (
            <option key={t.topic_id} value={t.topic_id}>
              {t.name}
            </option>
          ))}
        </select>
        <input
          aria-label="Part names"
          placeholder="Part A, Part B"
          value={parts}
          onChange={(e) => setParts(e.target.value)}
          className="border px-1"
        />
        <button
          disabled={!splitId || names.length < 2}
          onClick={() =>
            split.mutate(
              { versionId, topicId: splitId, names },
              { onSuccess: () => setParts(""), onError: notify.error },
            )
          }
        >
          Split
        </button>
      </fieldset>
    </section>
  );
}
