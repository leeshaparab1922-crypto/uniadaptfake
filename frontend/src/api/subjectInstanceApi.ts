import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { SubjectInstance, TeacherAssignmentRole } from "../types/subject";

export const SUBJECT_INSTANCES_KEY = "subject-instances";
export const TEACHERS_KEY = "teachers-list";

export interface TeacherUser {
  id: string;
  name: string;
  email: string;
}

export function useSubjectInstances() {
  return useQuery({
    queryKey: [SUBJECT_INSTANCES_KEY],
    queryFn: async () => {
      try {
        const res = await apiRequest<any>("/admin/subject-instances");
        return Array.isArray(res) ? (res as SubjectInstance[]) : res?.items || [];
      } catch {
        return [] as SubjectInstance[];
      }
    },
  });
}

export function useTeachers() {
  return useQuery({
    queryKey: [TEACHERS_KEY],
    queryFn: async () => {
      try {
        const res = await apiRequest<any>("/admin/subjects/teachers");
        return Array.isArray(res) ? (res as TeacherUser[]) : res?.items || [];
      } catch {
        return [] as TeacherUser[];
      }
    },
  });
}

export function useCreateTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; email: string }) =>
      apiRequest<TeacherUser>("/admin/subjects/teachers", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [TEACHERS_KEY] });
    },
  });
}

export function useCreateSubjectInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { subject_id: string; section_id: string }) =>
      apiRequest<SubjectInstance>("/admin/subject-instances", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [SUBJECT_INSTANCES_KEY] });
    },
  });
}

export function useActivateSubjectInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (subjectInstanceId: string) =>
      apiRequest<SubjectInstance>(`/admin/subject-instances/${subjectInstanceId}/activate`, {
        method: "POST",
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [SUBJECT_INSTANCES_KEY] });
    },
  });
}

export function useAssignTeacher() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      teacher_id: string;
      subject_instance_id: string;
      role: TeacherAssignmentRole;
    }) =>
      apiRequest("/admin/subject-instances/teacher-assignments", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [SUBJECT_INSTANCES_KEY] });
    },
  });
}

export function useSetSubjectOwner() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { subject_id: string; owner_teacher_id: string; reason?: string }) =>
      apiRequest("/admin/subject-instances/subject-owner", {
        method: "POST",
        body: payload,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [SUBJECT_INSTANCES_KEY] });
    },
  });
}