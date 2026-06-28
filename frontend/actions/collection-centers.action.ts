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

/** Translate a backend error into a Spanish, user-facing message. */
function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "ORG_MEMBERSHIP_REQUIRED":
        return "No eres miembro activo de esa organización.";
      case "COLLECTION_CENTER_NOT_FOUND":
        return "El centro de acopio ya no existe.";
      case "VALIDATION_ERROR":
        return "Revisa los datos del formulario e inténtalo de nuevo.";
      default:
        return "No se pudo completar la acción. Inténtalo de nuevo.";
    }
  }
  return "No se pudo completar la acción. Inténtalo de nuevo.";
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

  const name = String(formData.get("name") ?? "").trim();
  const address = String(formData.get("address") ?? "").trim();
  const country = String(formData.get("country") ?? "").trim();
  const city = String(formData.get("city") ?? "").trim();
  const contact = String(formData.get("contact") ?? "").trim();
  const openingHours = String(formData.get("opening_hours") ?? "").trim();
  const notes = String(formData.get("notes") ?? "").trim();

  if (!name || !address || !country || !city || !contact) {
    return { error: "Completa todos los campos obligatorios." };
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
    return { error: messageFor(error) };
  }

  revalidatePath(CENTERS_PATH);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(CENTERS_PATH);
}

/** Verify a collection center (maintainer/admin). */
export async function verifyCenterAction(
  centerId: string,
): Promise<{ error: string | null }> {
  const token = await requireMaintainerToken();
  try {
    await centersApi.verifyCollectionCenter(token, centerId);
  } catch (error) {
    return { error: messageFor(error) };
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
  try {
    await centersApi.revokeCollectionCenterVerification(token, centerId);
  } catch (error) {
    return { error: messageFor(error) };
  }
  revalidatePath(CENTERS_PATH);
  revalidatePath(`${CENTERS_PATH}/${centerId}`);
  return { error: null };
}
