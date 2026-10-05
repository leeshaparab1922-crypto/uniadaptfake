import { useRetryIngestion, useVersionDetail } from "../../api/contentApi";
import { useNotify } from "../../hooks/useNotify";

/** Ingestion has no interactive UI of its own (OCR/clean/chunk/embed are background stages):
 * the Teacher sees this per-stage timeline, the failed stage/page message, and a Retry button. */
export default function IngestionStatus({ versionId }: { versionId: string }) {
  const { data, isLoading, isError } = useVersionDetail(versionId);
  const retry = useRetryIngestion();
  const notify = useNotify();
  if (isLoading) return <p className="text-sm">Loading status...</p>;
  if (isError || !data)
    return (
      <p role="alert" className="text-sm">
        Could not load ingestion status.
      </p>
    );

  const latest = Math.max(0, ...data.stage_runs.map((r) => r.attempt));
  const runs = data.stage_runs.filter((r) => r.attempt === latest);
  return (
    <div data-testid="ingestion-status" className="space-y-1 text-sm">
      <p>
        Version {data.version_no}: <strong>{data.ingestion_status}</strong> ({data.chunk_count}{" "}
        chunks)
      </p>
      <ol className="list-decimal pl-5">
        {runs.map((r) => (
          <li key={r.stage}>
            {r.stage}: {r.status}
            {r.stage === "OCR" &&
              Array.isArray(r.detail?.ocr_pages) &&
              ` (${(r.detail.ocr_pages as number[]).length} pages OCR'd)`}
          </li>
        ))}
        {runs.length === 0 && <li>Queued, waiting for a worker.</li>}
      </ol>
      {data.ingestion_status === "FAILED" && (
        <div role="alert" className="rounded border border-red-300 bg-red-50 p-2">
          <p>
            Failed at {data.failed_stage}: {data.failure_message}
          </p>
        </div>
      )}
      {data.ingestion_status === "RUNNING" && !data.can_retry && data.retry_available_at && (
        <p data-testid="stuck-hint" className="text-gray-700">
          If this stays stuck, Retry becomes available at{" "}
          {new Date(data.retry_available_at).toLocaleString()}.
        </p>
      )}
      {data.ingestion_status === "RUNNING" && data.can_retry && (
        <p role="alert">Processing has stopped responding. You can retry it.</p>
      )}
      {data.can_retry && (
        <button
          className="mt-1 rounded border px-2 py-1"
          disabled={retry.isPending}
          onClick={() =>
            retry.mutate(versionId, {
              onSuccess: () => notify.success("Retry queued."),
              onError: notify.error,
            })
          }
        >
          Retry
        </button>
      )}
    </div>
  );
}
