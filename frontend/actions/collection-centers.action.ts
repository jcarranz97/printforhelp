"use server";

/**
 * Server actions for the collection centers domain. Each action re-reads
 * the auth cookie and re-verifies the caller server-side (NFR-006) before
 * forwarding to the backend: anyone authenticated may register a center;
 * only maintainers/admins may verify or revoke verification.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { fetchMe } from "@/lib/auth.api";
import * as centersApi from "@/lib/collection-centers.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const CENTERS_PATH = "/centers";

export type CreateCenterState = { error: string | null };

/** Resolve a maintainer/admin token, redirecting everyone else away. */
async function requireMaintainerToken(): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    redirect(`/login?next=${CENTERS_PATH}`);
  }
  const me = await fetchMe(token);
  if (!me || (me.role !== "maintainer" && me.role !== "admin")) {
    redirect(CENTERS_PATH);
  }
  return token;
}

/** Translate a backend error into a localized, user-facing message. */
function messageFor(error: unknown, t: Dictionary["centerForm"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "ORG_MEMBERSHIP_REQUIRED":
        return t.errorOrgMembership;
      case "COLLECTION_CENTER_NOT_FOUND":
        return t.errorNotFound;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/**
 * Register a new (unverified) collection center. Open to everyone: a
 * logged-in user owns it; a guest submits it anonymously. The token is
 * forwarded only when present.
 */
export async function createCenterAction(
  _prevState: CreateCenterState,
  formData: FormData,
): Promise<CreateCenterState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.centerForm;

  const name = String(formData.get("name") ?? "").trim();
  const address = String(formData.get("address") ?? "").trim();
  const country = String(formData.get("country") ?? "").trim();
  const city = String(formData.get("city") ?? "").trim();
  const contact = String(formData.get("contact") ?? "").trim();
  const openingHours = String(formData.get("opening_hours") ?? "").trim();
  const notes = String(formData.get("notes") ?? "").trim();

  if (!name || !address || !country || !city || !contact) {
    return { error: t.errorRequired };
  }

  try {
    await centersApi.createCollectionCenter(
      {
        name,
        address,
        country,
        city,
        contact,
        opening_hours: openingHours || undefined,
        notes: notes || undefined,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(CENTERS_PATH);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(CENTERS_PATH);
}

export type UpdateCenterState = { error: string | null };

/**
 * Edit an existing collection center (FR-031). Requires a session; the
 * backend re-checks that the caller is an effective member or a
 * maintainer/admin. `centerId` is bound by the caller via `.bind`.
 */
export async function updateCenterAction(
  centerId: string,
  _prevState: UpdateCenterState,
  formData: FormData,
): Promise<UpdateCenterState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.centerForm;

  if (!token) {
    redirect(`/login?next=${CENTERS_PATH}/${centerId}`);
  }

  const name = String(formData.get("name") ?? "").trim();
  const address = String(formData.get("address") ?? "").trim();
  const country = String(formData.get("country") ?? "").trim();
  const city = String(formData.get("city") ?? "").trim();
  const contact = String(formData.get("contact") ?? "").trim();
  const openingHours = String(formData.get("opening_hours") ?? "").trim();
  const notes = String(formData.get("notes") ?? "").trim();

  if (!name || !address || !country || !city || !contact) {
    return { error: t.errorRequired };
  }

  try {
    await centersApi.updateCollectionCenter(
      centerId,
      {
        name,
        address,
        country,
        city,
        contact,
        opening_hours: openingHours || null,
        notes: notes || null,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(CENTERS_PATH);
  revalidatePath(`${CENTERS_PATH}/${centerId}`);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(`${CENTERS_PATH}/${centerId}`);
}

/** Verify a collection center (maintainer/admin). */
export async function verifyCenterAction(
  centerId: string,
): Promise<{ error: string | null }> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await centersApi.verifyCollectionCenter(token, centerId);
  } catch (error) {
    return { error: messageFor(error, dict.centerForm) };
  }
  revalidatePath(CENTERS_PATH);
  revalidatePath(`${CENTERS_PATH}/${centerId}`);
  return { error: null };
}

/** Revoke a collection center's verification (maintainer/admin). */
export async function revokeCenterVerificationAction(
  centerId: string,
): Promise<{ error: string | null }> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await centersApi.revokeCollectionCenterVerification(token, centerId);
  } catch (error) {
    return { error: messageFor(error, dict.centerForm) };
  }
  revalidatePath(CENTERS_PATH);
  revalidatePath(`${CENTERS_PATH}/${centerId}`);
  return { error: null };
}
