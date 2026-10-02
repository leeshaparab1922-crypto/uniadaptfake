import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { ElectiveGroup, Subject, SubjectType, Unit } from "../types/subject";

export function useCreateElectiveGroup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { program_id: string; semester_no: number; name: string; required: boolean }) =>
      apiRequest<ElectiveGroup>("/admin/subjects/elective-groups", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
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
      elective_group_id: string | null;
    }) => apiRequest<Subject>("/admin/subjects", { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
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
      units: { order_index: number; name: string; weightage: number }[];
    }) => apiRequest<Unit[]>(`/admin/subjects/${subjectId}/units`, { method: "PUT", body: { units } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["subjects"] }),
  });
}
