/**
 * Thin fetch wrapper. The JWT lives only in an httpOnly cookie the backend
 * sets (ADR-0001) - this client never reads, stores, or logs it. Every
 * request sends cookies (`credentials: "include"`), and every
 * state-changing request echoes the non-httpOnly `csrf_token` cookie back
 * as the `X-CSRF-Token` header (double-submit CSRF, ADR-0001).
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

/** FastAPI returns `detail` as a string, or (422) a list of
 * `{loc, msg}` validation objects - flatten either into one readable line. */
function formatDetail(detail: unknown): string | undefined {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = detail.map((item) => {
      if (item && typeof item === "object" && "msg" in item) {
        const { loc, msg } = item as { loc?: unknown[]; msg: string };
        const field = Array.isArray(loc) ? loc.filter((p) => p !== "body").join(".") : "";
        return field ? `${field}: ${msg}` : msg;
      }
      return String(item);
    });
    return parts.join("; ");
  }
  return undefined;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  isFormData?: boolean;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};

  if (MUTATING_METHODS.has(method)) {
    const csrfToken = readCookie("csrf_token");
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  let body: BodyInit | undefined;
  if (options.body !== undefined) {
    if (options.isFormData) {
      body = options.body as FormData;
    } else {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    }
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body,
    credentials: "include",
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      detail = formatDetail(data.detail) ?? detail;
    } catch {
      // response body wasn't JSON - keep the generic status text.
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
