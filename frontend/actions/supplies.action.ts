"use server";

/**
 * Server actions for the Supplies catalog. Registering a supply requires a
 * session; the backend records the caller as creator and owner (FR-015) and
 * stamps it with `category = "other"` (see `lib/supplies.api.ts`).
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as suppliesApi from "@/lib/supplies.api";
import { uploadImage } from "@/lib/uploads.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const SUPPLIES_PATH = "/supplies";

export type CreateSupplyState = { error: string | null };
export type UpdateSupplyState = { error: string | null };

function messageFor(error: unknown, t: Dictionary["supplyForm"]): string {
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
 * Resolve the supply image URL: an attached file is uploaded and its stored
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

/** Split a comma-separated hidden field (from a TagInput) into a clean list. */
function parseList(raw: string): string[] {
  return raw
    ? raw
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean)
    : [];
}

function parseFields(formData: FormData) {
  const name = String(formData.get("name") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const imageUrl = String(formData.get("image_url") ?? "").trim();
  const units = parseList(String(formData.get("units") ?? "").trim());
  const tags = parseList(String(formData.get("tags") ?? "").trim());
  return { name, description, imageUrl, units, tags };
}

/** Register a new supply. Requires a session. */
export async function createSupplyAction(
  _prevState: CreateSupplyState,
  formData: FormData,
): Promise<CreateSupplyState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.supplyForm;

  if (!token) {
    redirect(`/login?next=${SUPPLIES_PATH}/new`);
  }

  const { name, description, imageUrl, units, tags } = parseFields(formData);
  if (!name) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await suppliesApi.createSupply(
      {
        name,
        description: description || undefined,
        image_url: resolvedImageUrl || undefined,
        units,
        tags,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(SUPPLIES_PATH);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(SUPPLIES_PATH);
}

/** Edit a supply (effective owner or maintainer/admin). `supplyId` is bound. */
export async function updateSupplyAction(
  supplyId: string,
  _prevState: UpdateSupplyState,
  formData: FormData,
): Promise<UpdateSupplyState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.supplyForm;

  if (!token) {
    redirect(`/login?next=${SUPPLIES_PATH}/${supplyId}/edit`);
  }

  const { name, description, imageUrl, units, tags } = parseFields(formData);
  if (!name) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await suppliesApi.updateSupply(
      supplyId,
      {
        name,
        description: description || null,
        image_url: resolvedImageUrl || null,
        units,
        tags,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(SUPPLIES_PATH);
  revalidatePath(`${SUPPLIES_PATH}/${supplyId}`);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(`${SUPPLIES_PATH}/${supplyId}`);
}
