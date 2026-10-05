import { useMySubjects } from "../../api/contentApi";

interface Props {
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** C1: lists only Subjects the Teacher is assigned to; the Owner badge is informational (server enforces). */
export default function TeacherSubjects({ selectedId, onSelect }: Props) {
  const { data, isLoading, isError } = useMySubjects();
  if (isLoading) return <p className="p-4 text-sm">Loading your subjects...</p>;
  if (isError)
    return (
      <p role="alert" className="p-4 text-sm">
        Could not load your subjects.
      </p>
    );
  const subjects = data ?? [];
  return (
    <div className="p-4">
      <h1 className="mb-2 text-lg font-semibold">My Subjects</h1>
      <ul data-testid="teacher-subjects" className="divide-y rounded border">
        {subjects.map((s) => (
          <li key={s.id} className="flex items-center justify-between p-3 text-sm">
            <span>
              {s.code} - {s.name}{" "}
              {s.is_owner && (
                <span
                  data-testid={`owner-badge-${s.id}`}
                  className="ml-2 rounded bg-green-100 px-2 py-0.5 text-xs"
                >
                  Subject Owner
                </span>
              )}
            </span>
            <button
              className={`rounded px-3 py-1 text-xs ${selectedId === s.id ? "bg-blue-600 text-white" : "border"}`}
              onClick={() => onSelect(s.id)}
            >
              Open content
            </button>
          </li>
        ))}
        {subjects.length === 0 && (
          <li className="p-3 text-sm text-gray-500">You are not assigned to any Subject.</li>
        )}
      </ul>
    </div>
  );
}
