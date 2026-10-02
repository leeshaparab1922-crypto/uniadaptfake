import { useState, type FormEvent } from "react";

import { useCreateElectiveGroup, useCreateSubject, useSetUnits } from "../../api/subjectApi";
import { useNotify } from "../../hooks/useNotify";
import type { SubjectType } from "../../types/subject";

/** FR-ADM-003: Subject/Unit catalogue, including elective groups. Unit
 * weight sum-to-100 is validated server-side (ADR-0002) - this form just
 * surfaces the resulting error. */
export default function SubjectCatalogue() {
  const createElectiveGroup = useCreateElectiveGroup();
  const createSubject = useCreateSubject();
  const setUnits = useSetUnits();
  const notify = useNotify();

  const [subjectId, setSubjectId] = useState("");
  const [unitsError, setUnitsError] = useState<string | null>(null);

  function submitElectiveGroup(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createElectiveGroup.mutate(
      {
        program_id: String(form.get("program_id")),
        semester_no: Number(form.get("semester_no")),
        name: String(form.get("name")),
        required: true,
      },
      {
        onSuccess: () => {
          formEl.reset();
          notify.success("Elective group created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitSubject(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createSubject.mutate(
      {
        program_id: String(form.get("program_id")),
        semester_no: Number(form.get("semester_no")),
        code: String(form.get("code")),
        name: String(form.get("name")),
        credits: Number(form.get("credits")),
        type: form.get("type") as SubjectType,
        elective_group_id: (form.get("elective_group_id") as string) || null,
      },
      {
        onSuccess: (data) => {
          setSubjectId(data.id);
          formEl.reset();
          notify.success("Subject created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitUnits(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setUnitsError(null);
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    const weights = String(form.get("weights"))
      .split(",")
      .map((w) => Number(w.trim()));
    setUnits.mutate(
      {
        subjectId,
        units: weights.map((weightage, index) => ({
          order_index: index + 1,
          name: `Unit ${index + 1}`,
          weightage,
        })),
      },
      {
        onSuccess: () => notify.success("Units saved."),
        onError: (err) => {
          setUnitsError(err instanceof Error ? err.message : "Failed to set units");
          notify.error(err);
        },
      },
    );
  }

  return (
    <div className="space-y-8 p-6" data-testid="subject-catalogue">
      <h1 className="text-lg font-semibold">Subject Catalogue</h1>

      <form onSubmit={submitElectiveGroup} className="space-x-2">
        <input name="program_id" placeholder="Program ID" required className="border px-2 py-1" />
        <input
          name="semester_no"
          type="number"
          min={1}
          step={1}
          placeholder="Semester #"
          required
          className="border px-2 py-1"
        />
        <input
          name="name"
          placeholder="Elective group name"
          required
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Elective Group
        </button>
      </form>

      <form onSubmit={submitSubject} className="space-x-2">
        <input name="program_id" placeholder="Program ID" required className="border px-2 py-1" />
        <input
          name="semester_no"
          type="number"
          min={1}
          step={1}
          placeholder="Semester #"
          required
          className="border px-2 py-1"
        />
        <input name="code" placeholder="Code" required className="border px-2 py-1" />
        <input name="name" placeholder="Name" required className="border px-2 py-1" />
        <input
          name="credits"
          type="number"
          min={0}
          step={1}
          placeholder="Credits"
          required
          className="border px-2 py-1"
        />
        <select name="type" className="border px-2 py-1">
          <option value="CORE">CORE</option>
          <option value="ELECTIVE">ELECTIVE</option>
          <option value="LAB">LAB</option>
        </select>
        <input
          name="elective_group_id"
          placeholder="Elective group ID (if elective)"
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Subject
        </button>
      </form>

      <form onSubmit={submitUnits} className="space-x-2">
        <input
          value={subjectId}
          onChange={(e) => setSubjectId(e.target.value)}
          placeholder="Subject ID"
          required
          className="border px-2 py-1"
        />
        <input
          name="weights"
          placeholder="Unit weights, comma-separated (must sum to 100)"
          required
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Set Units
        </button>
      </form>
      {unitsError && (
        <p role="alert" className="text-sm text-red-600">
          {unitsError}
        </p>
      )}
    </div>
  );
}
