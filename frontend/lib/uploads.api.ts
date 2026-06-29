/** Raw API call for uploading images (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

type ImageUploadResponse = { url: string };

/**
 * Upload an image file to the backend and return its stored public URL.
 * Server-side only — the bearer token is forwarded from the caller so the
 * JWT never leaves the server (httpOnly-cookie convention).
 */
export async function uploadImage(file: File, token: string): Promise<string> {
  const body = new FormData();
  body.append("file", file);
  // No explicit Content-Type: fetch sets the multipart boundary itself.
  const res = await fetch(`${apiBaseUrl()}/uploads/images`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return ((await res.json()) as ImageUploadResponse).url;
}
