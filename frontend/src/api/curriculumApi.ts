import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { CurriculumGraph, CurriculumVersion } from "../types/curriculum";
import { apiRequest } from "./client";

/** Hooks for the Teacher curriculum endpoints G1..G15. The server enforces assignment and
 * Subject-Owner rules; the UI only hides controls the caller cannot use. */

export function useCurriculumVersions(subjectId: string | null) {
  return useQuery({
    queryKey: ["teacher", "curriculum", "versions", subjectId],
    enabled: !!subjectId,
    queryFn: () =>
      apiRequest<CurriculumVersion[]>(`/teacher/subjects/${subjectId}/curriculum/versions`),
    refetchInterval: (query) =>
      query.state.data?.some((v) => v.status === "GENERATING") ? 3000 : false,
  });
}

export function useCurriculumGraph(versionId: string | null) {
  return useQuery({
    queryKey: ["teacher", "curriculum", "graph", versionId],
    enabled: !!versionId,
    queryFn: () => apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${versionId}`),
  });
}

function useInvalidating<TVars, TOut>(fn: (v: TVars) => Promise<TOut>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["teacher", "curriculum"] }),
  });
}

export function useGenerateCurriculum() {
  return useInvalidating((subjectId: string) =>
    apiRequest<CurriculumVersion>(`/teacher/subjects/${subjectId}/curriculum/generate`, {
      method: "POST",
    }),
  );
}

export function useRevalidate() {
  return useInvalidating((versionId: string) =>
    apiRequest<unknown>(`/teacher/curriculum/versions/${versionId}/validate`, { method: "POST" }),
  );
}

export interface TopicChanges {
  name?: string;
  classification?: string;
  est_hours?: number;
  unit_id?: string;
}

export function useEditTopic() {
  return useInvalidating((v: { versionId: string; topicId: string; changes: TopicChanges }) =>
    apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${v.versionId}/topics/${v.topicId}`, {
      method: "PATCH",
      body: v.changes,
    }),
  );
}

export function useDeleteTopic() {
  return useInvalidating((v: { versionId: string; topicId: string }) =>
    apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${v.versionId}/topics/${v.topicId}`, {
      method: "DELETE",
    }),
  );
}

export function useReorder() {
  return useInvalidating((v: { versionId: string; unitId: string; topicIds: string[] }) =>
    apiRequest<CurriculumGraph>(
      `/teacher/curriculum/versions/${v.versionId}/units/${v.unitId}/topic-order`,
      { method: "PUT", body: { topic_ids: v.topicIds } },
    ),
  );
}

export function useMerge() {
  return useInvalidating(
    (v: { versionId: string; topicIds: string[]; targetTopicId: string; name?: string }) =>
      apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${v.versionId}/topics/merge`, {
        method: "POST",
        body: { topic_ids: v.topicIds, target_topic_id: v.targetTopicId, name: v.name || null },
      }),
  );
}

export function useSplit() {
  return useInvalidating((v: { versionId: string; topicId: string; names: string[] }) =>
    apiRequest<CurriculumGraph>(
      `/teacher/curriculum/versions/${v.versionId}/topics/${v.topicId}/split`,
      { method: "POST", body: { parts: v.names.map((name) => ({ name })) } },
    ),
  );
}

export function useAddEdge() {
  return useInvalidating(
    (v: { versionId: string; topicId: string; prereqTopicId: string; confidence: number }) =>
      apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${v.versionId}/edges`, {
        method: "POST",
        body: { topic_id: v.topicId, prereq_topic_id: v.prereqTopicId, confidence: v.confidence },
      }),
  );
}

export function useDeleteEdge() {
  return useInvalidating((v: { versionId: string; edgeId: string }) =>
    apiRequest<CurriculumGraph>(`/teacher/curriculum/versions/${v.versionId}/edges/${v.edgeId}`, {
      method: "DELETE",
    }),
  );
}

export function useApproveCurriculum() {
  return useInvalidating((v: { versionId: string; reason: string }) =>
    apiRequest<CurriculumVersion>(`/teacher/curriculum/versions/${v.versionId}/approve`, {
      method: "POST",
      body: { reason: v.reason },
    }),
  );
}

export function useRejectCurriculum() {
  return useInvalidating((v: { versionId: string; reason: string }) =>
    apiRequest<CurriculumVersion>(`/teacher/curriculum/versions/${v.versionId}/reject`, {
      method: "POST",
      body: { reason: v.reason },
    }),
  );
}

export function useActivateFallback() {
  return useInvalidating((v: { subjectId: string; reason: string }) =>
    apiRequest<CurriculumVersion>(`/teacher/subjects/${v.subjectId}/curriculum/fallback`, {
      method: "POST",
      body: { reason: v.reason },
    }),
  );
}
