import { useState } from "react";

import { useActivateVersion, useRollback } from "../../api/contentApi";
import { useNotify } from "../../hooks/useNotify";
import type { ContentAsset, ContentVersion } from "../../types/content";

interface Props {
  isOwner: boolean;
  asset: ContentAsset;
  version: ContentVersion;
}

/** FR-CON-004: Activate / Rollback are rendered for the Subject Owner only. This is a convenience:
 * the server rejects any other caller (CO/unassigned) with 403/404 regardless of what the UI shows. */
export default function OwnerActions({ isOwner, asset, version }: Props) {
  const activate = useActivateVersion();
  const rollback = useRollback();
  const notify = useNotify();
  const [reason, setReason] = useState("");
  if (!isOwner) return null;

  const canActivate = version.status === "DRAFT" && version.ingestion_status === "SUCCEEDED";
  const canRollback = version.status === "SUPERSEDED" && version.ingestion_status === "SUCCEEDED";
  if (!canActivate && !canRollback) return null;

  return (
    <span className="space-x-1" data-testid="owner-actions">
      <input
        aria-label="Reason"
        placeholder="Reason"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        className="border px-1"
      />
      {canActivate && (
        <button
          onClick={() =>
            activate.mutate(
              { versionId: version.id, reason },
              { onSuccess: () => notify.success("Version activated."), onError: notify.error },
            )
          }
          className="rounded bg-green-700 px-2 text-white"
        >
          Activate
        </button>
      )}
      {canRollback && (
        <button
          onClick={() =>
            rollback.mutate(
              { assetId: asset.id, targetVersionId: version.id, reason },
              { onSuccess: () => notify.success("Rolled back."), onError: notify.error },
            )
          }
          className="rounded border px-2"
        >
          Roll back to this
        </button>
      )}
    </span>
  );
}
