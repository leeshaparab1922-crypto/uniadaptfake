import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { EnrollmentOut, PromotionPreviewResponse } from "../types/enrollment";

/** FR-STU-001: read-only. There is deliberately no mutation hook here that
 * a Student component could call - see `pages/student/MySubjects.tsx`. */
export function useMyEnrollments() {
  return useQuery({
    queryKey: ["enrollments", "me"],
    queryFn: () => apiRequest<EnrollmentOut[]>("/enrollments/me"),
  });
}

export function useAutoEnroll() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (studentId: string) =>
      apiRequest<EnrollmentOut[]>(`/admin/enrollments/auto-enroll/${studentId}`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enrollments"] }),
  });
}

export function useAssignElective() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { student_id: string; elective_group_id: string; subject_id: string }) =>
      apiRequest<EnrollmentOut>("/admin/enrollments/electives", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enrollments"] }),
  });
}

export interface PromotionRequestBody {
  student_ids: string[];
  to_batch_id: string;
  to_semester_no: number;
  to_section_id: string;
}

export function usePreviewPromotion() {
  return useMutation({
    mutationFn: (payload: PromotionRequestBody) =>
      apiRequest<PromotionPreviewResponse>("/admin/enrollments/promotion/preview", { method: "POST", body: payload }),
  });
}

export function useConfirmPromotion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: PromotionRequestBody) =>
      apiRequest<{ operation_id: string }>("/admin/enrollments/promotion/confirm", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["enrollments"] }),
  });
}
