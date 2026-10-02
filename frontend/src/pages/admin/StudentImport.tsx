import { useRef, useState, type FormEvent } from "react";

import { useImportStudents, useStudents } from "../../api/studentApi";
import { useNotify } from "../../hooks/useNotify";

const PAGE_SIZE = 25;

/** FR-ADM-005: CSV import with per-row error reporting (ADR-0005), plus a
 * read-only list of students so an Admin can confirm what was imported. */
export default function StudentImport() {
  const importStudents = useImportStudents();
  const notify = useNotify();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [offset, setOffset] = useState(0);
  const students = useStudents(PAGE_SIZE, offset);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const file = fileInputRef.current?.files?.[0];
    if (file) {
      importStudents.mutate(file, {
        onSuccess: (summary) => {
          formEl.reset();
          setOffset(0);
          if (summary.errors.length > 0) {
            notify.error(
              new Error(`Imported ${summary.created} student(s); ${summary.errors.length} row(s) failed.`),
            );
          } else {
            notify.success(`Imported ${summary.created} student(s).`);
          }
        },
        onError: notify.error,
      });
    }
  }

  const total = students.data?.total ?? 0;

  return (
    <div className="space-y-4 p-6" data-testid="student-import">
      <h1 className="text-lg font-semibold">Student CSV Import</h1>
      <form onSubmit={handleSubmit} className="space-x-2">
        <input ref={fileInputRef} type="file" accept=".csv" required data-testid="csv-file-input" />
        <button type="submit" disabled={importStudents.isPending} className="rounded bg-blue-600 px-3 py-1 text-white">
          {importStudents.isPending ? "Importing..." : "Import"}
        </button>
      </form>

      {importStudents.data && (
        <div data-testid="import-summary">
          <p>Created: {importStudents.data.created}</p>
          {importStudents.data.errors.length > 0 && (
            <ul className="mt-2 list-disc pl-5 text-sm text-red-600">
              {importStudents.data.errors.map((err) => (
                <li key={err.row_number}>
                  Row {err.row_number}: {err.reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <section data-testid="student-list" className="space-y-2">
        <h2 className="font-semibold">Students ({total})</h2>
        {students.isLoading && <p className="text-sm">Loading students...</p>}
        {students.isError && (
          <p role="alert" className="text-sm text-red-600">
            Failed to load students.
          </p>
        )}
        {students.data && students.data.items.length === 0 && (
          <p className="text-sm text-gray-600">No students yet. Import a CSV above.</p>
        )}
        {students.data && students.data.items.length > 0 && (
          <>
            <table className="min-w-full border text-sm">
              <thead>
                <tr>
                  <th className="border px-2 py-1 text-left">Roll #</th>
                  <th className="border px-2 py-1 text-left">Name</th>
                  <th className="border px-2 py-1 text-left">Email</th>
                  <th className="border px-2 py-1 text-left">Semester</th>
                  <th className="border px-2 py-1 text-left">Section ID</th>
                </tr>
              </thead>
              <tbody>
                {students.data.items.map((s) => (
                  <tr key={s.id}>
                    <td className="border px-2 py-1">{s.roll_number}</td>
                    <td className="border px-2 py-1">{s.full_name}</td>
                    <td className="border px-2 py-1">{s.email}</td>
                    <td className="border px-2 py-1">{s.current_semester_no}</td>
                    <td className="border px-2 py-1">{s.section_id}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="space-x-2">
              <button
                type="button"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="rounded border px-3 py-1 disabled:opacity-50"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={offset + PAGE_SIZE >= total}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="rounded border px-3 py-1 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
