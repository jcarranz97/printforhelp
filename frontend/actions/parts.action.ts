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
import { uploadFile, uploadImage } from "@/lib/uploads.api";
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
      case "FILE_TOO_LARGE":
        return t.errorFileTooLarge;
      case "UNSUPPORTED_FILE_TYPE":
        return t.errorFileType;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/**
 * Read the Part image focal point (percent, 0-100 on each axis) the form
 * submits as hidden `image_focus_x` / `image_focus_y` fields. Falls back to
 * the center (50) when absent or out of range.
 */
function parseImageFocus(formData: FormData): { x: number; y: number } {
  const read = (name: string): number => {
    const value = Number(formData.get(name));
    return Number.isFinite(value) && value >= 0 && value <= 100 ? value : 50;
  };
  return { x: read("image_focus_x"), y: read("image_focus_y") };
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

/**
 * Resolve the Part label image URL (the print-on-the-package banner): an
 * attached file is uploaded and its stored URL wins; otherwise the pasted
 * URL is used as a fallback.
 */
async function resolveLabelImageUrl(
  formData: FormData,
  pastedUrl: string,
  token: string,
): Promise<string> {
  const file = formData.get("label_file");
  if (file instanceof File && file.size > 0) {
    return uploadImage(file, token);
  }
  return pastedUrl;
}

/**
 * Resolve the Part source URL: an attached model file is uploaded to our
 * own storage and its URL wins (so the "download" link points at us);
 * otherwise the pasted link (MakerWorld, Drive, ...) is used.
 */
async function resolveSourceUrl(
  formData: FormData,
  pastedUrl: string,
  token: string,
): Promise<string> {
  const file = formData.get("source_file");
  if (file instanceof File && file.size > 0) {
    return uploadFile(file, token);
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
  const labelUrl = String(formData.get("label_image_url") ?? "").trim();
  const focus = parseImageFocus(formData);
  const tagsRaw = String(formData.get("tags") ?? "").trim();
  const tags = tagsRaw
    ? tagsRaw
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    : [];

  if (!name) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedSourceUrl = await resolveSourceUrl(
      formData,
      sourceUrl,
      token,
    );
    if (!resolvedSourceUrl) {
      return { error: t.errorRequired };
    }
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    const resolvedLabelUrl = await resolveLabelImageUrl(
      formData,
      labelUrl,
      token,
    );
    await partsApi.createPart(
      {
        name,
        source_url: resolvedSourceUrl,
        description: description || undefined,
        image_url: resolvedImageUrl || undefined,
        image_focus_x: focus.x,
        image_focus_y: focus.y,
        label_image_url: resolvedLabelUrl || undefined,
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

/** Archive a Part (effective owner or maintainer/admin). */
export async function archivePartAction(
  partId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.resourceArchive;

  if (!token) {
    redirect(`/login?next=${PARTS_PATH}/${partId}/edit`);
  }

  try {
    await partsApi.archivePart(partId, token);
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.code === "RESOURCE_ARCHIVE_BLOCKED"
    ) {
      return { error: t.errorBlocked };
    }
    return { error: t.errorGeneric };
  }

  revalidatePath(PARTS_PATH);
  revalidatePath(`${PARTS_PATH}/${partId}`);
  return { error: null };
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
  const labelUrl = String(formData.get("label_image_url") ?? "").trim();
  const focus = parseImageFocus(formData);
  const tagsRaw = String(formData.get("tags") ?? "").trim();
  const tags = tagsRaw
    ? tagsRaw
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean)
    : [];

  if (!name) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedSourceUrl = await resolveSourceUrl(
      formData,
      sourceUrl,
      token,
    );
    if (!resolvedSourceUrl) {
      return { error: t.errorRequired };
    }
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    const resolvedLabelUrl = await resolveLabelImageUrl(
      formData,
      labelUrl,
      token,
    );
    await partsApi.updatePart(
      partId,
      {
        name,
        source_url: resolvedSourceUrl,
        description: description || null,
        image_url: resolvedImageUrl || null,
        image_focus_x: focus.x,
        image_focus_y: focus.y,
        label_image_url: resolvedLabelUrl || null,
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
