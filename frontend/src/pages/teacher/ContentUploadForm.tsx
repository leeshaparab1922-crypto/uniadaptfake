import { useState } from "react";

import { ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES, useUpload } from "../../api/contentApi";
import { useNotify } from "../../hooks/useNotify";
import type { AssignedSubject, ContentAsset } from "../../types/content";

interface Props {
  subject: AssignedSubject;
  assets: ContentAsset[];
}

const TYPES = ["SYLLABUS", "NOTES", "PPT", "PYQ", "LAB"];
const ALL_UNITS = "__all__";

/** FR-CON-001: client-side pre-checks mirror the server (the server remains authoritative). */
export default function ContentUploadForm({ subject, assets }: Props) {
  const notify = useNotify();
  const upload = useUpload();
  const [file, setFile] = useState<File | null>(null);
  const [contentType, setContentType] = useState("NOTES");
  const [title, setTitle] = useState("");
  const [unitId, setUnitId] = useState("");
  const [assetId, setAssetId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const candidates = assets.filter((a) => a.content_type === contentType);

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) return setError("Choose a file to upload.");
    const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
    if (!ALLOWED_EXTENSIONS.includes(ext)) return setError("Allowed types: PDF, PPTX, DOCX, TXT.");
    if (file.size > MAX_UPLOAD_BYTES) return setError("File exceeds the 25 MB limit.");
    if (file.size === 0) return setError("The file is empty.");
    if (!assetId && !title.trim()) return setError("Enter a title for a new asset.");
    const isSyllabus = contentType === "SYLLABUS";
    if (!isSyllabus && !unitId) return setError("Choose the Unit this file covers, or All units.");
    upload.mutate(
      {
        subjectId: subject.id,
        file,
        contentType,
        title,
        unitId: !isSyllabus && unitId && unitId !== ALL_UNITS ? unitId : undefined,
        allUnits: !isSyllabus && unitId === ALL_UNITS,
        assetId: assetId || undefined,
      },
      {
        onSuccess: () => {
          notify.success("Uploaded as DRAFT. Ingestion has been queued.");
          setFile(null);
        },
        onError: (err) => notify.error(err),
      },
    );
  }

  return (
    <form
      onSubmit={submit}
      data-testid="upload-form"
      className="space-y-2 rounded border p-3 text-sm"
    >
      <h2 className="font-semibold">Upload content</h2>
      <input
        aria-label="File"
        type="file"
        accept=".pdf,.pptx,.docx,.txt"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />
      <label className="block">
        Type
        <select
          aria-label="Content type"
          value={contentType}
          onChange={(e) => {
            setContentType(e.target.value);
            setAssetId("");
          }}
          className="ml-2 border"
        >
          {TYPES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </label>
      {contentType === "SYLLABUS" ? (
        <p className="text-gray-700">
          A syllabus covers all Units; Units are read from its &quot;Unit 1&quot;, &quot;Unit
          2&quot; headings.
        </p>
      ) : (
        <label className="block">
          Unit
          <select
            aria-label="Unit"
            value={unitId}
            onChange={(e) => setUnitId(e.target.value)}
            className="ml-2 border"
          >
            <option value="">Choose a Unit</option>
            <option value={ALL_UNITS}>All units (file has Unit headings)</option>
            {subject.units.map((u) => (
              <option key={u.id} value={u.id}>
                {u.order_index}. {u.name}
              </option>
            ))}
          </select>
        </label>
      )}
      <label className="block">
        New version of
        <select
          aria-label="Existing asset"
          value={assetId}
          onChange={(e) => setAssetId(e.target.value)}
          className="ml-2 border"
        >
          <option value="">New asset</option>
          {candidates.map((a) => (
            <option key={a.id} value={a.id}>
              {a.title}
            </option>
          ))}
        </select>
      </label>
      {!assetId && (
        <label className="block">
          Title
          <input
            aria-label="Title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="ml-2 border"
          />
        </label>
      )}
      {error && (
        <p role="alert" className="text-red-700">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={upload.isPending}
        className="rounded bg-blue-600 px-3 py-1 text-white"
      >
        Upload
      </button>
    </form>
  );
}
