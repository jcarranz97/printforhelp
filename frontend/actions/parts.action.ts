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
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
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
    await partsApi.createPart(
      {
        name,
        source_url: sourceUrl,
        description: description || undefined,
        image_url: imageUrl || undefined,
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
