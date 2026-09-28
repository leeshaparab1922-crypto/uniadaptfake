import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";

export interface ImportSummary {
  created: number;
  errors: { row_number: number; reason: string }[];
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
