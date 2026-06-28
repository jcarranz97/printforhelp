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
