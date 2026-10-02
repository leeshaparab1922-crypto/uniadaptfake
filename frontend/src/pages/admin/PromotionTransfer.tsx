import { useState, type FormEvent } from "react";

import {
  useConfirmPromotion,
  usePreviewPromotion,
  type PromotionRequestBody,
} from "../../api/enrollmentApi";
import { useNotify } from "../../hooks/useNotify";
import type { PromotionPreviewResponse } from "../../types/enrollment";

/** FR-ADM-006 / BUS-049: promotion/Section transfer with a mandatory
 * preview step before any mutation, preserving history. */
export default function PromotionTransfer() {
  const previewPromotion = usePreviewPromotion();
  const confirmPromotion = useConfirmPromotion();
  const notify = useNotify();
  const [preview, setPreview] = useState<PromotionPreviewResponse | null>(null);
  const [lastRequest, setLastRequest] = useState<PromotionRequestBody | null>(null);

  function buildRequest(form: FormData): PromotionRequestBody {
    return {
      student_ids: String(form.get("student_ids"))
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      to_batch_id: String(form.get("to_batch_id")),
      to_semester_no: Number(form.get("to_semester_no")),
      to_section_id: String(form.get("to_section_id")),
    };
  }

  function submitPreview(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const request = buildRequest(new FormData(e.currentTarget));
    setLastRequest(request);
    previewPromotion.mutate(request, {
      onSuccess: (data) => setPreview(data),
      onError: notify.error,
    });
  }

  function handleConfirm() {
    if (lastRequest) {
      confirmPromotion.mutate(lastRequest, {
        onSuccess: () => {
          setPreview(null);
          setLastRequest(null);
          notify.success("Promotion / transfer confirmed.");
        },
        onError: notify.error,
      });
    }
  }

  return (
    <div className="space-y-6 p-6" data-testid="promotion-transfer">
      <h1 className="text-lg font-semibold">Promotion / Section Transfer</h1>

      <form onSubmit={submitPreview} className="space-x-2">
        <input
          name="student_ids"
          placeholder="Student IDs, comma-separated"
          required
          className="border px-2 py-1"
        />
        <input
          name="to_batch_id"
          placeholder="Target Batch ID"
          required
          className="border px-2 py-1"
        />
        <input
          name="to_semester_no"
          type="number"
          min={1}
          step={1}
          placeholder="Target semester #"
          required
          className="border px-2 py-1"
        />
        <input
          name="to_section_id"
          placeholder="Target Section ID"
          required
          className="border px-2 py-1"
        />
        <button type="submit" className="rounded bg-blue-600 px-3 py-1 text-white">
          Preview
        </button>
      </form>

      {preview && (
        <div data-testid="promotion-preview">
          <table className="min-w-full border text-sm">
            <thead>
              <tr>
                <th className="border px-2 py-1">Roll #</th>
                <th className="border px-2 py-1">From Section</th>
                <th className="border px-2 py-1">To Section</th>
                <th className="border px-2 py-1">Conflict?</th>
              </tr>
            </thead>
            <tbody>
              {preview.items.map((item) => (
                <tr key={item.student_id}>
                  <td className="border px-2 py-1">{item.roll_number}</td>
                  <td className="border px-2 py-1">{item.from_section_id}</td>
                  <td className="border px-2 py-1">{item.to_section_id}</td>
                  <td className="border px-2 py-1">{item.capacity_conflict ? "YES" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={preview.has_conflicts || confirmPromotion.isPending}
            className="mt-3 rounded bg-green-600 px-3 py-1 text-white disabled:opacity-50"
          >
            Confirm Promotion / Transfer
          </button>
          {preview.has_conflicts && (
            <p role="alert" className="mt-2 text-sm text-red-600">
              Resolve capacity conflicts before confirming.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
