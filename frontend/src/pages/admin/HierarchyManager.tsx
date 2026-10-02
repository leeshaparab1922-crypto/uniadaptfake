import { useState, type FormEvent } from "react";

import {
  useCreateBatch,
  useCreateDepartment,
  useCreateInstitute,
  useCreateProgram,
  useCreateSection,
  useCreateSemester,
  useBatches,
  useDepartments,
  useInstitutes,
  usePrograms,
  useSections,
  useSemesters,
} from "../../api/academicStructureApi";
import { useNotify } from "../../hooks/useNotify";

interface RecordListProps<T extends { id: string }> {
  testId: string;
  label: string;
  parentSelected: boolean;
  parentHint: string;
  query: { data?: T[]; isLoading: boolean; isError: boolean; error: Error | null };
  selectedId: string;
  onSelect?: (id: string) => void;
  describe: (row: T) => string;
}

/** Saved records for one hierarchy level. Clicking a row selects it as the
 * parent for the next level's form, so the page works after a reload. */
function RecordList<T extends { id: string }>({
  testId,
  label,
  parentSelected,
  parentHint,
  query,
  selectedId,
  onSelect,
  describe,
}: RecordListProps<T>) {
  const rows = query.data ?? [];
  return (
    <div data-testid={testId} className="text-sm">
      {!parentSelected ? (
        <p className="text-gray-500">{parentHint}</p>
      ) : query.isLoading ? (
        <p className="text-gray-500">Loading...</p>
      ) : query.isError ? (
        <p role="alert" className="text-red-600">
          {`Could not load ${label}: ${query.error?.message ?? "unknown error"}`}
        </p>
      ) : rows.length === 0 ? (
        <p className="text-gray-500">{`No ${label} yet.`}</p>
      ) : (
        <ul className="space-y-1">
          {rows.map((row) => (
            <li key={row.id}>
              {onSelect ? (
                <button
                  type="button"
                  aria-pressed={row.id === selectedId}
                  onClick={() => onSelect(row.id)}
                  className={`rounded border px-2 py-1 ${row.id === selectedId ? "bg-blue-100" : ""}`}
                >
                  {describe(row)}
                </button>
              ) : (
                <span className="px-2 py-1">{describe(row)}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/** FR-ADM-001: Institute -> Department -> Program -> Batch -> Semester ->
 * Section hierarchy maintenance. Numeric input bounds mirror the backend
 * Pydantic constraints (duration_semesters/number/capacity > 0). */
export default function HierarchyManager() {
  const createInstitute = useCreateInstitute();
  const createDepartment = useCreateDepartment();
  const createProgram = useCreateProgram();
  const createBatch = useCreateBatch();
  const createSemester = useCreateSemester();
  const createSection = useCreateSection();
  const notify = useNotify();

  const [instituteId, setInstituteId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [programId, setProgramId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [semesterId, setSemesterId] = useState("");

  const institutes = useInstitutes();
  const departments = useDepartments(instituteId);
  const programs = usePrograms(departmentId);
  const batches = useBatches(programId);
  const semesters = useSemesters(batchId);
  const sections = useSections(semesterId);

  // Choosing a parent clears every deeper selection.
  function pickInstitute(id: string) {
    setInstituteId(id);
    setDepartmentId("");
    setProgramId("");
    setBatchId("");
    setSemesterId("");
  }
  function pickDepartment(id: string) {
    setDepartmentId(id);
    setProgramId("");
    setBatchId("");
    setSemesterId("");
  }
  function pickProgram(id: string) {
    setProgramId(id);
    setBatchId("");
    setSemesterId("");
  }
  function pickBatch(id: string) {
    setBatchId(id);
    setSemesterId("");
  }

  function submitInstitute(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createInstitute.mutate(
      { name: String(form.get("name")), timezone: String(form.get("timezone") || "Asia/Kolkata") },
      {
        onSuccess: (data) => {
          pickInstitute(data.id);
          formEl.reset();
          notify.success("Institute created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitDepartment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createDepartment.mutate(
      { institute_id: instituteId, code: String(form.get("code")), name: String(form.get("name")) },
      {
        onSuccess: (data) => {
          pickDepartment(data.id);
          formEl.reset();
          notify.success("Department created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitProgram(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createProgram.mutate(
      {
        department_id: departmentId,
        code: String(form.get("code")),
        name: String(form.get("name")),
        duration_semesters: Number(form.get("duration_semesters")),
      },
      {
        onSuccess: (data) => {
          pickProgram(data.id);
          formEl.reset();
          notify.success("Program created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitBatch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createBatch.mutate(
      {
        program_id: programId,
        start_year: Number(form.get("start_year")),
        end_year: Number(form.get("end_year")),
      },
      {
        onSuccess: (data) => {
          pickBatch(data.id);
          formEl.reset();
          notify.success("Batch created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitSemester(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createSemester.mutate(
      {
        batch_id: batchId,
        number: Number(form.get("number")),
        start_date: String(form.get("start_date")),
        end_date: String(form.get("end_date")),
      },
      {
        onSuccess: (data) => {
          setSemesterId(data.id);
          formEl.reset();
          notify.success("Semester created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitSection(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createSection.mutate(
      {
        semester_id: semesterId,
        name: String(form.get("name")),
        capacity: Number(form.get("capacity")),
      },
      {
        onSuccess: () => {
          formEl.reset();
          notify.success("Section created.");
        },
        onError: notify.error,
      },
    );
  }

  return (
    <div className="space-y-8 p-6" data-testid="hierarchy-manager">
      <h1 className="text-lg font-semibold">Academic Hierarchy</h1>

      <form onSubmit={submitInstitute} className="space-x-2">
        <input name="name" placeholder="Institute name" required className="border px-2 py-1" />
        <input name="timezone" placeholder="Asia/Kolkata" className="border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Institute
        </button>
      </form>
      <RecordList
        testId="institute-list"
        label="institutes"
        parentSelected
        parentHint=""
        query={institutes}
        selectedId={instituteId}
        onSelect={pickInstitute}
        describe={(r) => `${r.name} (${r.timezone})`}
      />

      <form onSubmit={submitDepartment} className="space-x-2">
        <input
          name="code"
          placeholder="Dept code"
          required
          disabled={!instituteId}
          className="border px-2 py-1"
        />
        <input
          name="name"
          placeholder="Dept name"
          required
          disabled={!instituteId}
          className="border px-2 py-1"
        />
        <button
          type="submit"
          disabled={!instituteId}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Add Department
        </button>
      </form>
      <RecordList
        testId="department-list"
        label="departments"
        parentSelected={Boolean(instituteId)}
        parentHint="Select an institute to see its departments."
        query={departments}
        selectedId={departmentId}
        onSelect={pickDepartment}
        describe={(r) => `${r.code} - ${r.name}`}
      />

      <form onSubmit={submitProgram} className="space-x-2">
        <input
          name="code"
          placeholder="Program code"
          required
          disabled={!departmentId}
          className="border px-2 py-1"
        />
        <input
          name="name"
          placeholder="Program name"
          required
          disabled={!departmentId}
          className="border px-2 py-1"
        />
        <input
          name="duration_semesters"
          type="number"
          min={1}
          step={1}
          placeholder="Duration (semesters)"
          required
          disabled={!departmentId}
          className="border px-2 py-1"
        />
        <button
          type="submit"
          disabled={!departmentId}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Add Program
        </button>
      </form>
      <RecordList
        testId="program-list"
        label="programs"
        parentSelected={Boolean(departmentId)}
        parentHint="Select a department to see its programs."
        query={programs}
        selectedId={programId}
        onSelect={pickProgram}
        describe={(r) => `${r.code} - ${r.name} (${r.duration_semesters} semesters)`}
      />

      <form onSubmit={submitBatch} className="space-x-2">
        <input
          name="start_year"
          type="number"
          min={1900}
          max={2200}
          step={1}
          placeholder="Start year"
          required
          disabled={!programId}
          className="border px-2 py-1"
        />
        <input
          name="end_year"
          type="number"
          min={1900}
          max={2200}
          step={1}
          placeholder="End year"
          required
          disabled={!programId}
          className="border px-2 py-1"
        />
        <button
          type="submit"
          disabled={!programId}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Add Batch
        </button>
      </form>
      <RecordList
        testId="batch-list"
        label="batches"
        parentSelected={Boolean(programId)}
        parentHint="Select a program to see its batches."
        query={batches}
        selectedId={batchId}
        onSelect={pickBatch}
        describe={(r) => `${r.start_year}-${r.end_year}`}
      />

      <form onSubmit={submitSemester} className="space-x-2">
        <input
          name="number"
          type="number"
          min={1}
          step={1}
          placeholder="Semester #"
          required
          disabled={!batchId}
          className="border px-2 py-1"
        />
        <input
          name="start_date"
          type="date"
          required
          disabled={!batchId}
          className="border px-2 py-1"
        />
        <input
          name="end_date"
          type="date"
          required
          disabled={!batchId}
          className="border px-2 py-1"
        />
        <button
          type="submit"
          disabled={!batchId}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Add Semester
        </button>
      </form>
      <RecordList
        testId="semester-list"
        label="semesters"
        parentSelected={Boolean(batchId)}
        parentHint="Select a batch to see its semesters."
        query={semesters}
        selectedId={semesterId}
        onSelect={setSemesterId}
        describe={(r) => `Semester ${r.number} (${r.start_date} to ${r.end_date})`}
      />

      <form onSubmit={submitSection} className="space-x-2">
        <input
          name="name"
          placeholder="Section name"
          required
          disabled={!semesterId}
          className="border px-2 py-1"
        />
        <input
          name="capacity"
          type="number"
          min={1}
          step={1}
          placeholder="Capacity"
          required
          disabled={!semesterId}
          className="border px-2 py-1"
        />
        <button
          type="submit"
          disabled={!semesterId}
          className="rounded bg-blue-600 px-3 py-1 text-white"
        >
          Add Section
        </button>
      </form>
      <RecordList
        testId="section-list"
        label="sections"
        parentSelected={Boolean(semesterId)}
        parentHint="Select a semester to see its sections."
        query={sections}
        selectedId=""
        describe={(r) => `${r.name} (capacity ${r.capacity})`}
      />
    </div>
  );
}
