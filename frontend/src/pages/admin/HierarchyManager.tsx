import { useState, type FormEvent } from "react";

import {
  useCreateBatch,
  useCreateDepartment,
  useCreateInstitute,
  useCreateProgram,
  useCreateSection,
  useCreateSemester,
} from "../../api/academicStructureApi";

/** FR-ADM-001: Institute -> Department -> Program -> Batch -> Semester ->
 * Section hierarchy maintenance. */
export default function HierarchyManager() {
  const createInstitute = useCreateInstitute();
  const createDepartment = useCreateDepartment();
  const createProgram = useCreateProgram();
  const createBatch = useCreateBatch();
  const createSemester = useCreateSemester();
  const createSection = useCreateSection();

  const [instituteId, setInstituteId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [programId, setProgramId] = useState("");
  const [batchId, setBatchId] = useState("");
  const [semesterId, setSemesterId] = useState("");

  function submitInstitute(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createInstitute.mutate(
      { name: String(form.get("name")), timezone: String(form.get("timezone") || "Asia/Kolkata") },
      { onSuccess: (data) => setInstituteId(data.id) },
    );
  }

  function submitDepartment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createDepartment.mutate(
      { institute_id: instituteId, code: String(form.get("code")), name: String(form.get("name")) },
      { onSuccess: (data) => setDepartmentId(data.id) },
    );
  }

  function submitProgram(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createProgram.mutate(
      {
        department_id: departmentId,
        code: String(form.get("code")),
        name: String(form.get("name")),
        duration_semesters: Number(form.get("duration_semesters")),
      },
      { onSuccess: (data) => setProgramId(data.id) },
    );
  }

  function submitBatch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createBatch.mutate(
      {
        program_id: programId,
        start_year: Number(form.get("start_year")),
        end_year: Number(form.get("end_year")),
      },
      { onSuccess: (data) => setBatchId(data.id) },
    );
  }

  function submitSemester(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createSemester.mutate(
      {
        batch_id: batchId,
        number: Number(form.get("number")),
        start_date: String(form.get("start_date")),
        end_date: String(form.get("end_date")),
      },
      { onSuccess: (data) => setSemesterId(data.id) },
    );
  }

  function submitSection(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createSection.mutate({
      semester_id: semesterId,
      name: String(form.get("name")),
      capacity: Number(form.get("capacity")),
    });
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
        <input name="code" placeholder="Dept code" required disabled={!instituteId} className="border px-2 py-1" />
        <input name="name" placeholder="Dept name" required disabled={!instituteId} className="border px-2 py-1" />
        <button type="submit" disabled={!instituteId} className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Department
        </button>
      </form>

      <form onSubmit={submitProgram} className="space-x-2">
        <input name="code" placeholder="Program code" required disabled={!departmentId} className="border px-2 py-1" />
        <input name="name" placeholder="Program name" required disabled={!departmentId} className="border px-2 py-1" />
        <input
          name="duration_semesters"
          type="number"
          placeholder="Duration (semesters)"
          required
          disabled={!departmentId}
          className="border px-2 py-1"
        />
        <button type="submit" disabled={!departmentId} className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Program
        </button>
      </form>

      <form onSubmit={submitBatch} className="space-x-2">
        <input name="start_year" type="number" placeholder="Start year" required disabled={!programId} className="border px-2 py-1" />
        <input name="end_year" type="number" placeholder="End year" required disabled={!programId} className="border px-2 py-1" />
        <button type="submit" disabled={!programId} className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Batch
        </button>
      </form>

      <form onSubmit={submitSemester} className="space-x-2">
        <input name="number" type="number" placeholder="Semester #" required disabled={!batchId} className="border px-2 py-1" />
        <input name="start_date" type="date" required disabled={!batchId} className="border px-2 py-1" />
        <input name="end_date" type="date" required disabled={!batchId} className="border px-2 py-1" />
        <button type="submit" disabled={!batchId} className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Semester
        </button>
      </form>

      <form onSubmit={submitSection} className="space-x-2">
        <input name="name" placeholder="Section name" required disabled={!semesterId} className="border px-2 py-1" />
        <input name="capacity" type="number" placeholder="Capacity" required disabled={!semesterId} className="border px-2 py-1" />
        <button type="submit" disabled={!semesterId} className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Section
        </button>
      </form>
    </div>
  );
}
