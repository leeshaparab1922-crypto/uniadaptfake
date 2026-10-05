import { useState } from "react";

import { useAssets } from "../../api/contentApi";
import type { AssignedSubject } from "../../types/content";
import ChunkViewer from "./ChunkViewer";
import ContentUploadForm from "./ContentUploadForm";
import IngestionStatus from "./IngestionStatus";
import OwnerActions from "./OwnerActions";
import ResourceLinks from "./ResourceLinks";

/** Assets and versions of one shared Subject with status badges (DRAFT / ACTIVE / SUPERSEDED). */
export default function SubjectContent({ subject }: { subject: AssignedSubject }) {
  const { data: assets, isLoading, isError } = useAssets(subject.id);
  const [selected, setSelected] = useState<string | null>(null);

  if (isLoading) return <p className="p-4 text-sm">Loading content...</p>;
  if (isError)
    return (
      <p role="alert" className="p-4 text-sm">
        Could not load content.
      </p>
    );

  return (
    <div className="space-y-4 p-4 text-sm">
      <h1 className="text-lg font-semibold">{subject.code} content</h1>
      <ContentUploadForm subject={subject} assets={assets ?? []} />
      {(assets ?? []).map((asset) => (
        <section key={asset.id} className="rounded border p-2" data-testid={`asset-${asset.id}`}>
          <h2 className="font-semibold">
            {asset.title} ({asset.content_type})
          </h2>
          <ul>
            {asset.versions.map((v) => (
              <li key={v.id} className="flex items-center justify-between border-t py-1">
                <span>
                  v{v.version_no} - {v.original_filename}{" "}
                  <span className="rounded bg-gray-100 px-1" data-testid={`status-${v.id}`}>
                    {v.status}
                  </span>{" "}
                  <span className="text-gray-500">ingestion {v.ingestion_status}</span>
                </span>
                <span className="space-x-2">
                  <button className="underline" onClick={() => setSelected(v.id)}>
                    Details
                  </button>
                  <OwnerActions isOwner={subject.is_owner} asset={asset} version={v} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {selected && (
        <div className="space-y-2 rounded border p-2">
          <IngestionStatus versionId={selected} />
          <ChunkViewer versionId={selected} />
        </div>
      )}
      <ResourceLinks subjectId={subject.id} isOwner={subject.is_owner} units={subject.units} />
    </div>
  );
}
