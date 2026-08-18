/**
 * Low-level API helpers shared by the server-side data layer.
 *
 * Server actions and route handlers talk to the backend through the
 * internal Docker network URL (`API_URL_INTERNAL`); browser code falls
 * back to the public URL (`NEXT_PUBLIC_API_URL`).
 */

export const AUTH_COOKIE_NAME = "pforh_token";

/** Base URL of the backend API (`.../api/v1`). */
export function apiBaseUrl(): string {
  return (
    process.env.API_URL_INTERNAL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://localhost:8100/api/v1"
  );
}

/**
 * Default ceiling for a single backend call, in milliseconds.
 *
 * A bare `fetch` has no timeout at all: if the backend stalls, the promise
 * never settles. The campaign page fans out three calls per item, so a stalled
 * backend used to leave those requests pending forever, piling up until the
 * Node process was wedged — indistinguishable from a crash, and not something
 * `restart: unless-stopped` recovers from. Bounding each call turns that into a
 * normal error the boundary can render.
 */
export const API_TIMEOUT_MS = 15_000;

/** Thrown when a backend call exceeds its timeout. */
export class ApiTimeoutError extends Error {
  constructor(url: string, timeoutMs: number) {
    super(`Backend request timed out after ${timeoutMs}ms: ${url}`);
    this.name = "ApiTimeoutError";
  }
}

/**
 * `fetch` with a bounded lifetime. Drop-in replacement for the raw call.
 *
 * Pass `timeoutMs` to widen the ceiling for genuinely slow endpoints (file
 * uploads, PDF bundle rendering). An explicit `signal` on `init` still wins:
 * it is chained, so the caller can abort earlier than the timeout.
 */
export async function apiFetch(
  url: string,
  init?: RequestInit & { timeoutMs?: number },
): Promise<Response> {
  const { timeoutMs = API_TIMEOUT_MS, signal, ...rest } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  // Chain any caller-supplied signal so both can abort the request. Check
  // `aborted` up front too: a signal that fired before we got here would never
  // emit the event, and the request would run on regardless.
  const onCallerAbort = () => controller.abort();
  if (signal?.aborted) {
    controller.abort();
  } else {
    signal?.addEventListener("abort", onCallerAbort);
  }
  try {
    return await fetch(url, { ...rest, signal: controller.signal });
  } catch (err) {
    // Distinguish "we gave up" from "the caller cancelled" — only the former
    // is a backend problem worth surfacing as a timeout.
    if (
      controller.signal.aborted &&
      !signal?.aborted &&
      err instanceof Error &&
      err.name === "AbortError"
    ) {
      throw new ApiTimeoutError(url, timeoutMs);
    }
    throw err;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", onCallerAbort);
  }
}

/** Error thrown when the backend returns a non-2xx response. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

type ErrorEnvelope = {
  error?: { code?: string; message?: string };
};

/** Parse a backend error envelope into an {@link ApiError}. */
export async function toApiError(res: Response): Promise<ApiError> {
  let body: ErrorEnvelope | null = null;
  try {
    body = (await res.json()) as ErrorEnvelope;
  } catch {
    body = null;
  }
  return new ApiError(
    res.status,
    body?.error?.code ?? "UNKNOWN",
    body?.error?.message ?? "Ocurrió un error inesperado.",
  );
}
