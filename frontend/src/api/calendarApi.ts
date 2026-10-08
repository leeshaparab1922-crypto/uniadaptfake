import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { AcademicCalendarOut, SlotType, TimetableSlotOut } from "../types/calendar";

export function useCreateAcademicCalendar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      semester_id: string;
      holidays: string[];
      ia_window_start: string;
      ia_window_end: string;
      practical_window_start: string;
      practical_window_end: string;
      university_exam_window_start: string;
      university_exam_window_end: string;
    }) => apiRequest<AcademicCalendarOut>("/admin/calendar", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar"] }),
  });
}

export function useAddTimetableSlot() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      section_id: string;
      subject_instance_id: string | null;
      day_of_week: number;
      start_time: string;
      end_time: string;
      type: SlotType;
      effective_from: string;
      effective_to: string | null;
    }) => apiRequest<TimetableSlotOut>("/admin/calendar/timetable-slots", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["calendar"] }),
  });
}
