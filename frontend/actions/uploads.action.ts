"use server";

/**
 * Server action for inline image uploads from the Markdown editor.
 *
 * The Markdown editor is a client component, but the JWT lives in an
 * httpOnly cookie the browser cannot read, so the actual upload must run
 * server-side. The client sends the pasted/dropped file here; we forward
 * the bearer token to the backend `POST /uploads/images` and return the
 * stored public URL the editor then inserts as `![](url)`.
 *
 * Errors are returned as a stable `errorCode` the client maps to a
 * localized message (so this action stays locale-agnostic).
 */

import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { uploadImage } from "@/lib/uploads.api";

export type UploadImageResult = { url: string } | { errorCode: string };

export async function uploadMarkdownImageAction(
  formData: FormData,
): Promise<UploadImageResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { errorCode: "AUTH" };
  }
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { errorCode: "NO_FILE" };
  }
  try {
    const url = await uploadImage(file, token);
    return { url };
  } catch (error) {
    if (error instanceof ApiError) {
      return { errorCode: error.code };
    }
    return { errorCode: "UPLOAD" };
  }
}
