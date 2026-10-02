import { useState, type FormEvent } from "react";

import {
  useCreateBatch,
  useCreateDepartment,
  useCreateInstitute,
  useCreateProgram,
  useCreateSection,
  useCreateSemester,
} from "../../api/academicStructureApi";
import { useNotify } from "../../hooks/useNotify";

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

  function submitInstitute(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createInstitute.mutate(
      { name: String(form.get("name")), timezone: String(form.get("timezone") || "Asia/Kolkata") },
      {
        onSuccess: (data) => {
          setInstituteId(data.id);
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
          setDepartmentId(data.id);
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
          setProgramId(data.id);
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
          setBatchId(data.id);
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
    </div>
  );
}
