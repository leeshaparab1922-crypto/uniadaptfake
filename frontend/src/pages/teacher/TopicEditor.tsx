import { useState } from "react";

import { useDeleteTopic, useEditTopic, useReorder } from "../../api/curriculumApi";
import { useNotify } from "../../hooks/useNotify";
import type { Classification, CurriculumGraph, CurriculumTopic } from "../../types/curriculum";

/** FR-CUR-003: rename, classify, hours, assign Unit, reorder, delete. Editable while DRAFT/RETURNED. */
export default function TopicEditor({ graph }: { graph: CurriculumGraph }) {
  const edit = useEditTopic();
  const del = useDeleteTopic();
  const reorder = useReorder();
  const notify = useNotify();
  const editable = graph.version.status === "DRAFT" || graph.version.status === "RETURNED";
  const versionId = graph.version.id;
  const apply = (topicId: string, changes: Parameters<typeof edit.mutate>[0]["changes"]) =>
    edit.mutate({ versionId, topicId, changes }, { onError: notify.error });

  const move = (t: CurriculumTopic, delta: number) => {
    const siblings = graph.topics.filter((x) => x.unit_id === t.unit_id);
    const ids = siblings.map((x) => x.topic_id);
    const i = ids.indexOf(t.topic_id);
    const j = i + delta;
    if (!t.unit_id || j < 0 || j >= ids.length) return;
    [ids[i], ids[j]] = [ids[j], ids[i]];
    reorder.mutate({ versionId, unitId: t.unit_id, topicIds: ids }, { onError: notify.error });
  };

  return (
    <table className="w-full text-left" data-testid="topic-editor">
      <thead>
        <tr>
          <th>Topic</th>
          <th>Unit (weight)</th>
          <th>Class</th>
          <th>Hours</th>
          <th />
        </tr>
      </thead>
      <tbody>
        {graph.topics.map((t) => (
          <TopicRow
            key={`${t.topic_id}:${t.name}:${t.est_hours}:${t.classification}`}
            topic={t}
            graph={graph}
            editable={editable}
            onChange={(c) => apply(t.topic_id, c)}
            onMove={(d) => move(t, d)}
            onDelete={() =>
              del.mutate({ versionId, topicId: t.topic_id }, { onError: notify.error })
            }
          />
        ))}
      </tbody>
    </table>
  );
}

interface RowProps {
  topic: CurriculumTopic;
  graph: CurriculumGraph;
  editable: boolean;
  onChange: (c: {
    name?: string;
    classification?: string;
    est_hours?: number;
    unit_id?: string;
  }) => void;
  onMove: (delta: number) => void;
  onDelete: () => void;
}

function TopicRow({ topic, graph, editable, onChange, onMove, onDelete }: RowProps) {
  const [name, setName] = useState(topic.name);
  const [hours, setHours] = useState(String(topic.est_hours));
  const unit = graph.units.find((u) => u.id === topic.unit_id);
  return (
    <tr data-testid={`topic-${topic.topic_id}`}>
      <td>
        <input
          aria-label={`Name of ${topic.name}`}
          value={name}
          disabled={!editable}
          onChange={(e) => setName(e.target.value)}
          onBlur={() => name.trim() && name !== topic.name && onChange({ name })}
          className="border px-1"
        />
        {topic.is_orphan && <span className="ml-1 rounded bg-red-100 px-1">Orphan</span>}
      </td>
      <td>
        {editable ? (
          <select
            aria-label={`Unit of ${topic.name}`}
            value={topic.unit_id ?? ""}
            onChange={(e) => e.target.value && onChange({ unit_id: e.target.value })}
          >
            <option value="">(no Unit)</option>
            {graph.units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} ({u.weightage}%)
              </option>
            ))}
          </select>
        ) : (
          unit && `${unit.name} (${unit.weightage}%)`
        )}
      </td>
      <td>
        <select
          aria-label={`Classification of ${topic.name}`}
          value={topic.classification}
          disabled={!editable}
          onChange={(e) => onChange({ classification: e.target.value as Classification })}
        >
          <option value="CORE">Core</option>
          <option value="OPTIONAL">Optional</option>
          <option value="SELF_STUDY">Self-study</option>
        </select>
      </td>
      <td>
        <input
          aria-label={`Hours of ${topic.name}`}
          type="number"
          min="0.25"
          step="0.25"
          value={hours}
          disabled={!editable}
          onChange={(e) => setHours(e.target.value)}
          onBlur={() =>
            Number(hours) > 0 &&
            Number(hours) !== topic.est_hours &&
            onChange({ est_hours: Number(hours) })
          }
          className="w-16 border px-1"
        />
      </td>
      <td className="space-x-1">
        {editable && (
          <>
            <button aria-label={`Move ${topic.name} up`} onClick={() => onMove(-1)}>
              Up
            </button>
            <button aria-label={`Move ${topic.name} down`} onClick={() => onMove(1)}>
              Down
            </button>
            <button aria-label={`Remove ${topic.name}`} onClick={onDelete}>
              Remove
            </button>
          </>
        )}
      </td>
    </tr>
  );
}
