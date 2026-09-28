import { useMutation, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type { Batch, Department, Institute, Program, Section, Semester } from "../types/academicStructure";

const BASE = "/admin/academic-structure";

export function useCreateInstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; timezone: string }) =>
      apiRequest<Institute>(`${BASE}/institutes`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}

export function useCreateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { institute_id: string; code: string; name: string }) =>
      apiRequest<Department>(`${BASE}/departments`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}

export function useCreateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { department_id: string; code: string; name: string; duration_semesters: number }) =>
      apiRequest<Program>(`${BASE}/programs`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}

export function useCreateBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { program_id: string; start_year: number; end_year: number }) =>
      apiRequest<Batch>(`${BASE}/batches`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}

export function useCreateSemester() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { batch_id: string; number: number; start_date: string; end_date: string }) =>
      apiRequest<Semester>(`${BASE}/semesters`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}

export function useCreateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { semester_id: string; name: string; capacity: number }) =>
      apiRequest<Section>(`${BASE}/sections`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["academic-structure"] }),
  });
}
