import { useMyEnrollments } from "../../api/enrollmentApi";

/**
 * FR-STU-001 / BUS-001: read-only. This component renders zero add/drop/
 * mutate controls anywhere in its tree, and the only hook it imports
 * (`useMyEnrollments`) has no corresponding mutation - there is nothing to
 * wire a button to even by mistake.
 */
export default function MySubjects() {
  const { data: enrollments, isLoading, isError } = useMyEnrollments();

  if (isLoading) {
    return <p>Loading your subjects...</p>;
  }
  if (isError) {
    return <p role="alert">Could not load your subjects.</p>;
  }

  return (
    <div className="p-6">
      <h1 className="mb-4 text-lg font-semibold">My Subjects</h1>
      <p className="mb-4 text-sm text-gray-500">
        This list is set by your Department/Admin. You cannot add or drop a subject yourself.
      </p>
      <ul data-testid="my-subjects-list" className="divide-y divide-gray-200 rounded border">
        {(enrollments ?? []).map((enrollment) => (
          <li key={enrollment.id} className="p-3 text-sm">
            Subject instance: {enrollment.subject_instance_id} - {enrollment.status}
            {enrollment.auto_allocated ? " (auto-allocated)" : ""}
          </li>
        ))}
        {(enrollments ?? []).length === 0 && <li className="p-3 text-sm text-gray-500">No subjects yet.</li>}
      </ul>
    </div>
  );
}
