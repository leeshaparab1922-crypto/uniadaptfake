import { useState } from "react";

import { useChunkReference, useChunks } from "../../api/contentApi";

/** FR-CON-003: chunk metadata (unit, locator, type) and a "Resolve citation" view that maps a chunk id
 * back to its version, file and locator, for any version status. */
export default function ChunkViewer({ versionId }: { versionId: string }) {
  const { data, isLoading, isError } = useChunks(versionId);
  const [resolveId, setResolveId] = useState<string | null>(null);
  const ref = useChunkReference(resolveId);

  if (isLoading) return <p className="text-sm">Loading chunks...</p>;
  if (isError)
    return (
      <p role="alert" className="text-sm">
        Could not load chunks.
      </p>
    );
  const chunks = data ?? [];
  return (
    <div className="text-sm">
      <table data-testid="chunk-table" className="w-full border">
        <thead>
          <tr className="bg-gray-50 text-left">
            <th>#</th>
            <th>Unit</th>
            <th>Locator</th>
            <th>Type</th>
            <th>Tokens</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {chunks.map((c) => (
            <tr key={c.id} className="border-t">
              <td>{c.chunk_index}</td>
              <td>{c.unit_no ?? "unresolved"}</td>
              <td>{c.locator}</td>
              <td>{c.chunk_type}</td>
              <td>{c.token_count}</td>
              <td>
                <button className="underline" onClick={() => setResolveId(c.id)}>
                  Resolve citation
                </button>
              </td>
            </tr>
          ))}
          {chunks.length === 0 && (
            <tr>
              <td colSpan={6} className="p-2 text-gray-500">
                No chunks yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {ref.data && (
        <aside data-testid="citation" className="mt-2 rounded border bg-gray-50 p-2">
          Version {ref.data.version_no} ({ref.data.version_status}) - {ref.data.source_file} -{" "}
          {ref.data.locator}
        </aside>
      )}
    </div>
  );
}
