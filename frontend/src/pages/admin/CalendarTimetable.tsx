import type { FormEvent } from "react";

import { useAddTimetableSlot, useCreateAcademicCalendar } from "../../api/calendarApi";
import type { SlotType } from "../../types/calendar";

/** FR-ADM-007: Academic calendar (term/IA/practical/university-exam
 * windows) and Section timetable slots (CLASS/LAB only - ADR-0007). */
export default function CalendarTimetable() {
  const createCalendar = useCreateAcademicCalendar();
  const addSlot = useAddTimetableSlot();

  function submitCalendar(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    createCalendar.mutate({
      semester_id: String(form.get("semester_id")),
      holidays: [],
      ia_window_start: String(form.get("ia_window_start")),
      ia_window_end: String(form.get("ia_window_end")),
      practical_window_start: String(form.get("practical_window_start")),
      practical_window_end: String(form.get("practical_window_end")),
      university_exam_window_start: String(form.get("university_exam_window_start")),
      university_exam_window_end: String(form.get("university_exam_window_end")),
    });
  }

  function submitSlot(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    addSlot.mutate({
      section_id: String(form.get("section_id")),
      subject_instance_id: null,
      day_of_week: Number(form.get("day_of_week")),
      start_time: String(form.get("start_time")),
      end_time: String(form.get("end_time")),
      type: form.get("type") as SlotType,
      effective_from: String(form.get("effective_from")),
      effective_to: null,
    });
  }

  return (
    <div className="space-y-8 p-6" data-testid="calendar-timetable">
      <h1 className="text-lg font-semibold">Academic Calendar &amp; Timetable</h1>

      <form onSubmit={submitCalendar} className="grid max-w-2xl grid-cols-2 gap-2">
        <input name="semester_id" placeholder="Semester ID" required className="col-span-2 border px-2 py-1" />
        <input name="ia_window_start" type="date" required className="border px-2 py-1" />
        <input name="ia_window_end" type="date" required className="border px-2 py-1" />
        <input name="practical_window_start" type="date" required className="border px-2 py-1" />
        <input name="practical_window_end" type="date" required className="border px-2 py-1" />
        <input name="university_exam_window_start" type="date" required className="border px-2 py-1" />
        <input name="university_exam_window_end" type="date" required className="border px-2 py-1" />
        <button type="submit" className="col-span-2 rounded bg-blue-600 px-3 py-1 text-white">
          Save Academic Calendar
        </button>
      </form>

      <form onSubmit={submitSlot} className="space-x-2">
        <input name="section_id" placeholder="Section ID" required className="border px-2 py-1" />
        <input name="day_of_week" type="number" min={0} max={6} placeholder="Day (0=Mon)" required className="border px-2 py-1" />
        <input name="start_time" type="time" required className="border px-2 py-1" />
        <input name="end_time" type="time" required className="border px-2 py-1" />
        <select name="type" className="border px-2 py-1">
          <option value="CLASS">CLASS</option>
          <option value="LAB">LAB</option>
        </select>
        <input name="effective_from" type="date" required className="border px-2 py-1" />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Add Timetable Slot
        </button>
      </form>
    </div>
  );
}
