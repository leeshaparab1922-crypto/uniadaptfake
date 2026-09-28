import { useRef, type FormEvent } from "react";

import { useImportStudents } from "../../api/studentApi";

/** FR-ADM-005: CSV import with per-row error reporting (ADR-0005). */
export default function StudentImport() {
  const importStudents = useImportStudents();
  const fileInputRef = useRef<HTMLInputElement>(null);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const file = fileInputRef.current?.files?.[0];
    if (file) {
      importStudents.mutate(file);
    }
  }

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
    </div>
  );
}
