import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { SubjectInstance, TeacherAssignmentRole } from "../types/subject";

export function useCreateSubjectInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { subject_id: string; section_id: string }) =>
      apiRequest<SubjectInstance>("/admin/subject-instances", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subject-instances"] }),
  });
}

export function useActivateSubjectInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (subjectInstanceId: string) =>
      apiRequest<SubjectInstance>(`/admin/subject-instances/${subjectInstanceId}/activate`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subject-instances"] }),
  });
}

export function useAssignTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { teacher_id: string; subject_instance_id: string; role: TeacherAssignmentRole }) =>
      apiRequest("/admin/subject-instances/teacher-assignments", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subject-instances"] }),
  });
}

export function useSetSubjectOwner() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { subject_id: string; owner_teacher_id: string; reason?: string }) =>
      apiRequest("/admin/subject-instances/subject-owner", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subject-instances"] }),
  });
}
