import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { apiRequest } from "./client";
import type {
  Batch,
  Department,
  Institute,
  Program,
  Section,
  Semester,
} from "../types/academicStructure";

const BASE = "/admin/academic-structure";

/** Every list query key starts with this root, so a create mutation can
 * invalidate all hierarchy lists with one call. */
export const ACADEMIC_STRUCTURE_KEY = "academic-structure";

export function useInstitutes() {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "institutes"],
    queryFn: () => apiRequest<Institute[]>(`${BASE}/institutes`),
  });
}

export function useDepartments(instituteId: string) {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "departments", instituteId],
    queryFn: () =>
      apiRequest<Department[]>(
        `${BASE}/departments?institute_id=${encodeURIComponent(instituteId)}`,
      ),
    enabled: Boolean(instituteId),
  });
}

export function usePrograms(departmentId: string) {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "programs", departmentId],
    queryFn: () =>
      apiRequest<Program[]>(`${BASE}/programs?department_id=${encodeURIComponent(departmentId)}`),
    enabled: Boolean(departmentId),
  });
}

export function useBatches(programId: string) {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "batches", programId],
    queryFn: () =>
      apiRequest<Batch[]>(`${BASE}/batches?program_id=${encodeURIComponent(programId)}`),
    enabled: Boolean(programId),
  });
}

export function useSemesters(batchId: string) {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "semesters", batchId],
    queryFn: () =>
      apiRequest<Semester[]>(`${BASE}/semesters?batch_id=${encodeURIComponent(batchId)}`),
    enabled: Boolean(batchId),
  });
}

export function useSections(semesterId: string) {
  return useQuery({
    queryKey: [ACADEMIC_STRUCTURE_KEY, "sections", semesterId],
    queryFn: () =>
      apiRequest<Section[]>(`${BASE}/sections?semester_id=${encodeURIComponent(semesterId)}`),
    enabled: Boolean(semesterId),
  });
}

export function useCreateInstitute() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { name: string; timezone: string }) =>
      apiRequest<Institute>(`${BASE}/institutes`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}

export function useCreateDepartment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { institute_id: string; code: string; name: string }) =>
      apiRequest<Department>(`${BASE}/departments`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}

export function useCreateProgram() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      department_id: string;
      code: string;
      name: string;
      duration_semesters: number;
    }) => apiRequest<Program>(`${BASE}/programs`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}

export function useCreateBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { program_id: string; start_year: number; end_year: number }) =>
      apiRequest<Batch>(`${BASE}/batches`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}

export function useCreateSemester() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      batch_id: string;
      number: number;
      start_date: string;
      end_date: string;
    }) => apiRequest<Semester>(`${BASE}/semesters`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}

export function useCreateSection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { semester_id: string; name: string; capacity: number }) =>
      apiRequest<Section>(`${BASE}/sections`, { method: "POST", body: payload }),
    onSuccess: () => qc.invalidateQueries({ queryKey: [ACADEMIC_STRUCTURE_KEY] }),
  });
}
