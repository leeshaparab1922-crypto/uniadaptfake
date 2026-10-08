export type SlotType = "CLASS" | "LAB";

export interface AcademicCalendarOut {
  id: string;
  semester_id: string;
  version: number;
  holidays: string[];
  ia_window_start: string;
  ia_window_end: string;
  practical_window_start: string;
  practical_window_end: string;
  university_exam_window_start: string;
  university_exam_window_end: string;
}

export interface TimetableSlotOut {
  id: string;
  section_id: string;
  subject_instance_id: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  type: SlotType;
  effective_from: string;
  effective_to: string | null;
}
