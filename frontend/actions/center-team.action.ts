"use server";

/**
 * Server actions for a Collection Center's team roster.
 *
 * Being on that roster is what lets someone act for the centre — take
 * delivery, pack boxes, dispatch them (FR-129). Adding and removing is
 * restricted to the centre's effective owner (FR-084); the backend is the real
 * boundary and re-checks every call (NFR-006).
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import {
  addCenterContributor,
  removeCenterContributor,
} from "@/lib/collection-centers.api";

export type TeamActionResult = { error: string | null };

function messageFor(error: unknown, t: Dictionary["centerTeam"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NOT_EFFECTIVE_OWNER":
        return t.errorNotOwner;
      case "USER_NOT_FOUND":
        return t.errorUserNotFound;
      case "ALREADY_MEMBER":
        return t.errorAlreadyMember;
      case "OWNER_CANNOT_LEAVE":
        return t.errorOwnerCannotLeave;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

async function tokenOrError(
  t: Dictionary["centerTeam"],
): Promise<{ token: string } | { error: string }> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { error: t.errorAuth };
  }
  return { token };
}

/** Add a contributor to a centre by username (effective owner, FR-084). */
export async function addContributorAction(
  centerId: string,
  username: string,
): Promise<TeamActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.centerTeam;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  const trimmed = username.trim();
  if (!trimmed) {
    return { error: t.errorUsernameRequired };
  }
  try {
    await addCenterContributor(auth.token, centerId, trimmed);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  return { error: null };
}

/** Remove a contributor (owner removes anyone; a contributor themselves). */
export async function removeContributorAction(
  centerId: string,
  userId: string,
): Promise<TeamActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.centerTeam;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await removeCenterContributor(auth.token, centerId, userId);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  return { error: null };
}
