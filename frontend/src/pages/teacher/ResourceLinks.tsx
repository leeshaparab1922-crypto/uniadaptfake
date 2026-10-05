import { useState } from "react";

import { useApproveLink, useLinks, useRegisterLink, useReviseLink } from "../../api/contentApi";
import { useNotify } from "../../hooks/useNotify";
import type { ResourceLink, ResourceLinkInput, UnitBrief } from "../../types/content";

interface Props {
  subjectId: string;
  isOwner: boolean;
  units?: UnitBrief[];
}

const RESOURCE_TYPES = ["ARTICLE", "VIDEO", "BOOK", "TUTORIAL", "OTHER"];

interface Draft {
  url: string;
  title: string;
  resourceType: string;
  unitId: string;
  topicLabel: string;
  minutes: string;
}

const EMPTY: Draft = {
  url: "",
  title: "",
  resourceType: "OTHER",
  unitId: "",
  topicLabel: "",
  minutes: "",
};

function fromLink(l: ResourceLink): Draft {
  return {
    url: l.url,
    title: l.title,
    resourceType: l.resource_type,
    unitId: l.unit_id ?? "",
    topicLabel: l.topic_label ?? "",
    minutes: l.est_minutes ? String(l.est_minutes) : "",
  };
}

/** Client pre-checks mirror the server (which stays authoritative). Returns an error or the input. */
function toInput(d: Draft): string | ResourceLinkInput {
  if (!d.url.trim().toLowerCase().startsWith("https://")) return "Only HTTPS links are allowed.";
  if (!d.title.trim()) return "Title is required.";
  const minutes = d.minutes.trim() ? Number(d.minutes) : null;
  if (minutes !== null && (!Number.isInteger(minutes) || minutes <= 0))
    return "Estimated minutes must be a positive whole number.";
  return {
    url: d.url.trim(),
    title: d.title.trim(),
    resource_type: d.resourceType,
    unit_id: d.unitId || null,
    topic_label: d.topicLabel.trim() || null,
    est_minutes: minutes,
  };
}

function LinkFields({
  draft,
  onChange,
  units,
  prefix,
}: {
  draft: Draft;
  onChange: (d: Draft) => void;
  units: UnitBrief[];
  prefix: string;
}) {
  const set = (patch: Partial<Draft>) => onChange({ ...draft, ...patch });
  return (
    <>
      <input
        aria-label={`${prefix}URL`}
        placeholder="https://..."
        value={draft.url}
        onChange={(e) => set({ url: e.target.value })}
        className="border px-1"
      />
      <input
        aria-label={`${prefix}title`}
        placeholder="Title"
        value={draft.title}
        onChange={(e) => set({ title: e.target.value })}
        className="border px-1"
      />
      <select
        aria-label={`${prefix}type`}
        value={draft.resourceType}
        onChange={(e) => set({ resourceType: e.target.value })}
        className="border"
      >
        {RESOURCE_TYPES.map((t) => (
          <option key={t}>{t}</option>
        ))}
      </select>
      <select
        aria-label={`${prefix}Unit`}
        value={draft.unitId}
        onChange={(e) => set({ unitId: e.target.value })}
        className="border"
      >
        <option value="">Any Unit</option>
        {units.map((u) => (
          <option key={u.id} value={u.id}>
            {u.order_index}. {u.name}
          </option>
        ))}
      </select>
      <input
        aria-label={`${prefix}topic`}
        placeholder="Topic (optional)"
        value={draft.topicLabel}
        onChange={(e) => set({ topicLabel: e.target.value })}
        className="border px-1"
      />
      <input
        aria-label={`${prefix}minutes`}
        placeholder="Minutes"
        inputMode="numeric"
        value={draft.minutes}
        onChange={(e) => set({ minutes: e.target.value })}
        className="w-20 border px-1"
      />
    </>
  );
}

/** FR-CON-001 / FR-CON-004 / BUS-047: recommendation-only HTTPS links (never fetched or embedded).
 * Approved links are never edited in place: "Revise" (shown for the APPROVED link only) creates a
 * new DRAFT with the edited values. Approve is shown to the Owner only. */
export default function ResourceLinks({ subjectId, isOwner, units = [] }: Props) {
  const { data } = useLinks(subjectId);
  const register = useRegisterLink();
  const revise = useReviseLink();
  const approve = useApproveLink();
  const notify = useNotify();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [revising, setRevising] = useState<{ id: string; draft: Draft } | null>(null);
  const [reviseError, setReviseError] = useState<string | null>(null);

  function add(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const input = toInput(draft);
    if (typeof input === "string") return setError(input);
    register.mutate(
      { subjectId, input },
      {
        onSuccess: () => {
          notify.success("Link saved as DRAFT.");
          setDraft(EMPTY);
        },
        onError: notify.error,
      },
    );
  }

  function saveRevision(e: React.FormEvent) {
    e.preventDefault();
    if (!revising) return;
    setReviseError(null);
    const input = toInput(revising.draft);
    if (typeof input === "string") return setReviseError(input);
    revise.mutate(
      { linkId: revising.id, input },
      {
        onSuccess: () => {
          notify.success("Revision saved as DRAFT. The approved link stays in use until approval.");
          setRevising(null);
        },
        onError: notify.error,
      },
    );
  }

  return (
    <section className="space-y-2 text-sm">
      <h2 className="font-semibold">Recommendation links</h2>
      <form onSubmit={add} data-testid="link-form" className="flex flex-wrap gap-2">
        <LinkFields draft={draft} onChange={setDraft} units={units} prefix="Link " />
        <button type="submit" className="rounded bg-blue-600 px-2 text-white">
          Add link
        </button>
      </form>
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      <ul data-testid="link-list" className="divide-y rounded border">
        {(data ?? []).map((l) => (
          <li key={l.id} className="space-y-1 p-2">
            <div className="flex items-center justify-between">
              <span>
                {l.title} - {l.url} [{l.status}]
              </span>
              <span className="space-x-2">
                {l.status === "APPROVED" && (
                  <button
                    className="underline"
                    onClick={() => {
                      setReviseError(null);
                      setRevising({ id: l.id, draft: fromLink(l) });
                    }}
                  >
                    Revise
                  </button>
                )}
                {isOwner && l.status === "DRAFT" && (
                  <button
                    className="underline"
                    onClick={() =>
                      approve.mutate(
                        { linkId: l.id, reason: "Approved" },
                        {
                          onSuccess: () => notify.success("Link approved."),
                          onError: notify.error,
                        },
                      )
                    }
                  >
                    Approve
                  </button>
                )}
              </span>
            </div>
            {revising?.id === l.id && (
              <form
                onSubmit={saveRevision}
                data-testid="revise-form"
                className="flex flex-wrap gap-2"
              >
                <LinkFields
                  draft={revising.draft}
                  onChange={(d) => setRevising({ id: l.id, draft: d })}
                  units={units}
                  prefix="Revised "
                />
                <button type="submit" className="rounded bg-blue-600 px-2 text-white">
                  Save revision
                </button>
                <button type="button" className="underline" onClick={() => setRevising(null)}>
                  Cancel
                </button>
                {reviseError && (
                  <p role="alert" className="w-full text-red-700">
                    {reviseError}
                  </p>
                )}
              </form>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
