import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { StudentListResponse } from "../types/student";

export interface ImportSummary {
  created: number;
  errors: { row_number: number; reason: string }[];
}

/** Read-only Admin list of students (FR-ADM-005 follow-up: verify imports). */
export function useStudents(limit: number, offset: number) {
  return useQuery({
    queryKey: ["students", { limit, offset }],
    queryFn: () => apiRequest<StudentListResponse>(`/admin/students?limit=${limit}&offset=${offset}`),
  });
}

export function useImportStudents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return apiRequest<ImportSummary>("/admin/students/import", {
        method: "POST",
        body: formData,
        isFormData: true,
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["students"] }),
  });
}
