import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { ElectiveGroup, Subject, SubjectType } from "../types/subject";

export const SUBJECTS_KEY = "subjects";

export function useSubjects(programId?: string) {
  return useQuery({
    queryKey: [SUBJECTS_KEY, programId ?? "all"],
    queryFn: async () => {
      try {
        const url = programId
          ? `/admin/subjects?program_id=${encodeURIComponent(programId)}`
          : "/admin/subjects";
        const res = await apiRequest<any>(url);
        return Array.isArray(res) ? (res as Subject[]) : res?.items || [];
      } catch {
        return [] as Subject[];
      }
    },
  });
}

export function useCreateElectiveGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      program_id: string;
      semester_no: number;
      name: string;
      required: boolean;
    }) => apiRequest<ElectiveGroup>("/admin/subjects/elective-groups", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [SUBJECTS_KEY] }),
  });
}

export function useCreateSubject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      program_id: string;
      semester_no: number;
      code: string;
      name: string;
      credits: number;
      type: SubjectType;
      elective_group_id?: string | null;
    }) => apiRequest<Subject>("/admin/subjects", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [SUBJECTS_KEY] }),
  });
}

export function useSetUnits() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      subjectId,
      units,
    }: {
      subjectId: string;
      units: Array<{ order_index: number; name: string; weightage: number }>;
    }) =>
      apiRequest(`/admin/subjects/${subjectId}/units`, {
        method: "PUT",
        body: { units },
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [SUBJECTS_KEY] }),
  });
}