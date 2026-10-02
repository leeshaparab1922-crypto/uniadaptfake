import type { FormEvent } from "react";

import {
  useActivateSubjectInstance,
  useAssignTeacher,
  useCreateSubjectInstance,
  useSetSubjectOwner,
} from "../../api/subjectInstanceApi";
import { useNotify } from "../../hooks/useNotify";
import type { TeacherAssignmentRole } from "../../types/subject";

/** FR-ADM-002 / FR-ADM-004: SubjectInstance mapping, Teacher assignment,
 * activation gate, and Subject Owner designation. */
export default function TeacherAssignment() {
  const createInstance = useCreateSubjectInstance();
  const activateInstance = useActivateSubjectInstance();
  const assignTeacher = useAssignTeacher();
  const setOwner = useSetSubjectOwner();
  const notify = useNotify();

  function submitInstance(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    createInstance.mutate(
      {
        subject_id: String(form.get("subject_id")),
        section_id: String(form.get("section_id")),
      },
      {
        onSuccess: () => {
          formEl.reset();
          notify.success("Subject instance created.");
        },
        onError: notify.error,
      },
    );
  }

  function submitAssignment(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    assignTeacher.mutate(
      {
        teacher_id: String(form.get("teacher_id")),
        subject_instance_id: String(form.get("subject_instance_id")),
        role: form.get("role") as TeacherAssignmentRole,
      },
      {
        onSuccess: () => {
          formEl.reset();
          notify.success("Teacher assigned.");
        },
        onError: notify.error,
      },
    );
  }

  function submitActivate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    activateInstance.mutate(String(form.get("subject_instance_id")), {
      onSuccess: () => {
        formEl.reset();
        notify.success("Subject instance activated.");
      },
      onError: notify.error,
    });
  }

  function submitOwner(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formEl = e.currentTarget;
    const form = new FormData(formEl);
    setOwner.mutate(
      {
        subject_id: String(form.get("subject_id")),
        owner_teacher_id: String(form.get("owner_teacher_id")),
      },
      {
        onSuccess: () => {
          formEl.reset();
          notify.success("Subject owner set.");
        },
        onError: notify.error,
      },
    );
  }

  return (
    <div className="space-y-8 p-6" data-testid="teacher-assignment">
      <h1 className="text-lg font-semibold">Teacher &amp; Subject Owner Assignment</h1>

      <form onSubmit={submitInstance} className="space-x-2">
        <input name="subject_id" placeholder="Subject ID" required className="border px-2 py-1" />
        <input name="section_id" placeholder="Section ID" required className="border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Create Subject Instance
        </button>
      </form>

      <form onSubmit={submitAssignment} className="space-x-2">
        <input name="teacher_id" placeholder="Teacher ID" required className="border px-2 py-1" />
        <input
          name="subject_instance_id"
          placeholder="SubjectInstance ID"
          required
          className="border px-2 py-1"
        />
        <select name="role" className="border px-2 py-1">
          <option value="PRIMARY">PRIMARY</option>
          <option value="CO">CO</option>
        </select>
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Assign Teacher
        </button>
      </form>

      <form onSubmit={submitActivate} className="space-x-2">
        <input
          name="subject_instance_id"
          placeholder="SubjectInstance ID"
          required
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-green-600 px-3 py-1 text-white">
          Activate (requires an assigned Teacher)
        </button>
      </form>

      <form onSubmit={submitOwner} className="space-x-2">
        <input name="subject_id" placeholder="Subject ID" required className="border px-2 py-1" />
        <input
          name="owner_teacher_id"
          placeholder="Owner Teacher ID"
          required
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Set Subject Owner (exactly one per Subject)
        </button>
      </form>
    </div>
  );
}
