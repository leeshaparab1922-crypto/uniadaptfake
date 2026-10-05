import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  AssignedSubject,
  Chunk,
  ChunkReference,
  ContentAsset,
  ContentVersion,
  ContentVersionDetail,
  ResourceLink,
  ResourceLinkInput,
} from "../types/content";
import { apiRequest } from "./client";

/** Hooks for the Teacher content endpoints C1..C13 (FR-CON-001..004). The server enforces
 * assignment and Subject-Owner rules; the UI only hides controls the caller cannot use. */

export const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
export const ALLOWED_EXTENSIONS = ["pdf", "pptx", "docx", "txt"];

export function useMySubjects() {
  return useQuery({
    queryKey: ["teacher", "subjects"],
    queryFn: () => apiRequest<AssignedSubject[]>("/teacher/subjects"),
  });
}

export function useAssets(subjectId: string | null) {
  return useQuery({
    queryKey: ["teacher", "assets", subjectId],
    enabled: !!subjectId,
    queryFn: () => apiRequest<ContentAsset[]>(`/teacher/subjects/${subjectId}/content/assets`),
  });
}

export function useVersionDetail(versionId: string | null) {
  return useQuery({
    queryKey: ["teacher", "version", versionId],
    enabled: !!versionId,
    queryFn: () => apiRequest<ContentVersionDetail>(`/teacher/content/versions/${versionId}`),
    refetchInterval: (query) => {
      const s = query.state.data?.ingestion_status;
      return s === "PENDING" || s === "RUNNING" ? 3000 : false;
    },
  });
}

export function useChunks(versionId: string | null) {
  return useQuery({
    queryKey: ["teacher", "chunks", versionId],
    enabled: !!versionId,
    queryFn: () => apiRequest<Chunk[]>(`/teacher/content/versions/${versionId}/chunks?limit=200`),
  });
}

export function useChunkReference(chunkId: string | null) {
  return useQuery({
    queryKey: ["teacher", "chunk-ref", chunkId],
    enabled: !!chunkId,
    queryFn: () => apiRequest<ChunkReference>(`/teacher/content/chunks/${chunkId}`),
  });
}

function useInvalidating<TVars, TOut>(fn: (v: TVars) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher"] }),
  });
}

export interface UploadInput {
  subjectId: string;
  file: File;
  contentType: string;
  title: string;
  unitId?: string;
  /** Explicit "All units" choice for a non-syllabus upload (finding m2). */
  allUnits?: boolean;
  assetId?: string;
}

export function useUpload() {
  return useInvalidating((v: UploadInput) => {
    const form = new FormData();
    form.append("file", v.file);
    form.append("content_type", v.contentType);
    form.append("title", v.title);
    if (v.unitId) form.append("unit_id", v.unitId);
    if (v.allUnits) form.append("all_units", "true");
    if (v.assetId) form.append("content_asset_id", v.assetId);
    return apiRequest<ContentVersion>(`/teacher/subjects/${v.subjectId}/content/uploads`, {
      method: "POST",
      body: form,
      isFormData: true,
    });
  });
}

export function useRetryIngestion() {
  return useInvalidating((versionId: string) =>
    apiRequest<ContentVersion>(`/teacher/content/versions/${versionId}/retry`, { method: "POST" }),
  );
}

export function useActivateVersion() {
  return useInvalidating((v: { versionId: string; reason: string }) =>
    apiRequest<ContentVersion>(`/teacher/content/versions/${v.versionId}/activate`, {
      method: "POST",
      body: { reason: v.reason },
    }),
  );
}

export function useRollback() {
  return useInvalidating((v: { assetId: string; targetVersionId: string; reason: string }) =>
    apiRequest<ContentVersion>(`/teacher/content/assets/${v.assetId}/rollback`, {
      method: "POST",
      body: { target_version_id: v.targetVersionId, reason: v.reason },
    }),
  );
}

export function useLinks(subjectId: string | null) {
  return useQuery({
    queryKey: ["teacher", "links", subjectId],
    enabled: !!subjectId,
    queryFn: () => apiRequest<ResourceLink[]>(`/teacher/subjects/${subjectId}/content/links`),
  });
}

export function useRegisterLink() {
  return useInvalidating((v: { subjectId: string; input: ResourceLinkInput }) =>
    apiRequest<ResourceLink>(`/teacher/subjects/${v.subjectId}/content/links`, {
      method: "POST",
      body: v.input,
    }),
  );
}

export function useReviseLink() {
  return useInvalidating((v: { linkId: string; input: ResourceLinkInput }) =>
    apiRequest<ResourceLink>(`/teacher/content/links/${v.linkId}/revisions`, {
      method: "POST",
      body: v.input,
    }),
  );
}

export function useApproveLink() {
  return useInvalidating((v: { linkId: string; reason: string }) =>
    apiRequest<ResourceLink>(`/teacher/content/links/${v.linkId}/approve`, {
      method: "POST",
      body: { reason: v.reason },
    }),
  );
}
