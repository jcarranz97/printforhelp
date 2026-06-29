"use server";

/**
 * Server actions for the Parts catalog. Registering a Part requires a
 * session; the backend records the caller as creator and owner (FR-015).
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as partsApi from "@/lib/parts.api";
import { uploadImage } from "@/lib/uploads.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const PARTS_PATH = "/parts";

export type CreatePartState = { error: string | null };

function messageFor(error: unknown, t: Dictionary["partForm"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "ORG_MEMBERSHIP_REQUIRED":
        return t.errorOrgMembership;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      case "IMAGE_TOO_LARGE":
        return t.errorImageTooLarge;
      case "INVALID_IMAGE":
        return t.errorImageInvalid;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/**
 * Resolve the Part image URL: an attached file is uploaded and its stored
 * URL wins; otherwise the optional pasted URL is used as a fallback.
 */
async function resolveImageUrl(
  formData: FormData,
  pastedUrl: string,
  token: string,
): Promise<string> {
  const file = formData.get("image_file");
  if (file instanceof File && file.size > 0) {
    return uploadImage(file, token);
  }
  return pastedUrl;
}

/** Register a new Part. Requires a session. */
export async function createPartAction(
  _prevState: CreatePartState,
  formData: FormData,
): Promise<CreatePartState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.partForm;

  if (!token) {
    redirect(`/login?next=${PARTS_PATH}/new`);
  }

  const name = String(formData.get("name") ?? "").trim();
  const sourceUrl = String(formData.get("source_url") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const imageUrl = String(formData.get("image_url") ?? "").trim();
  const tagsRaw = String(formData.get("tags") ?? "").trim();
  const tags = tagsRaw
    ? tagsRaw
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    : [];

  if (!name || !sourceUrl) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await partsApi.createPart(
      {
        name,
        source_url: sourceUrl,
        description: description || undefined,
        image_url: resolvedImageUrl || undefined,
        tags,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(PARTS_PATH);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(PARTS_PATH);
}

export type UpdatePartState = { error: string | null };

/** Edit a Part (effective owner or maintainer/admin). `partId` is bound. */
export async function updatePartAction(
  partId: string,
  _prevState: UpdatePartState,
  formData: FormData,
): Promise<UpdatePartState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.partForm;

  if (!token) {
    redirect(`/login?next=${PARTS_PATH}/${partId}/edit`);
  }

  const name = String(formData.get("name") ?? "").trim();
  const sourceUrl = String(formData.get("source_url") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const imageUrl = String(formData.get("image_url") ?? "").trim();
  const tagsRaw = String(formData.get("tags") ?? "").trim();
  const tags = tagsRaw
    ? tagsRaw
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    : [];

  if (!name || !sourceUrl) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await partsApi.updatePart(
      partId,
      {
        name,
        source_url: sourceUrl,
        description: description || null,
        image_url: resolvedImageUrl || null,
        tags,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(PARTS_PATH);
  revalidatePath(`${PARTS_PATH}/${partId}`);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(`${PARTS_PATH}/${partId}`);
}
