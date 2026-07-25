"use server";

/**
 * Server actions for item tracking. Generating tracking and changing
 * visibility require the maker (or an admin) — enforced server-side. Adding
 * a record after scanning is open per the token's visibility: a logged-in
 * caller is attributed (unless they opt out); a guest is always anonymous.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as trackingApi from "@/lib/tracking.api";
import type { TrackingVisibility } from "@/lib/tracking.api";

const MY_CONTRIBUTIONS_PATH = "/my-contributions";

export type TrackingState = { error: string | null; success?: boolean };

/** A quantity correction, carrying the resulting live-unit count. */
export type QuantityState = TrackingState & { trackedUnits?: number };

function messageFor(error: unknown, t: Dictionary["tracking"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "TRACKING_FORBIDDEN":
        return t.errorForbidden;
      case "TRACKING_ALREADY_EXISTS":
        return t.errorAlreadyExists;
      case "RECORD_EDIT_FORBIDDEN":
        return t.errorEditForbidden;
      case "NOT_RECEIVER":
        return t.errorNotReceiver;
      case "INVALID_TRANSITION":
        return t.errorAlreadyReceived;
      case "CENTER_REQUIRED":
        return t.errorCenterRequired;
      case "NOT_THE_MAKER":
        return t.errorQuantityForbidden;
      case "INVALID_UNIT_RANGE":
        return t.errorInvalidRange;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/** Parse a comma-separated tags field into a trimmed, non-empty list. */
function parseTags(raw: FormDataEntryValue | null): string[] {
  const value = String(raw ?? "").trim();
  if (!value) {
    return [];
  }
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

/** Generate the tracking group + one QR per unit for a Contribution. */
export async function generateTrackingAction(
  contributionId: string,
): Promise<TrackingState> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    redirect(`/login?next=${MY_CONTRIBUTIONS_PATH}/${contributionId}/tracking`);
  }
  try {
    await trackingApi.generateTracking(contributionId, token);
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
  revalidatePath(`${MY_CONTRIBUTIONS_PATH}/${contributionId}/tracking`);
  revalidatePath(MY_CONTRIBUTIONS_PATH);
  return { error: null, success: true };
}

/** Set visibility and the named group members. `groupId`/`contributionId` bound. */
export async function updateTrackingAction(
  groupId: string,
  contributionId: string,
  _prevState: TrackingState,
  formData: FormData,
): Promise<TrackingState> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    redirect(`/login?next=${MY_CONTRIBUTIONS_PATH}/${contributionId}/tracking`);
  }
  const visibility = String(
    formData.get("visibility") ?? "private",
  ) as TrackingVisibility;
  try {
    await trackingApi.updateTracking(
      groupId,
      { visibility, member_usernames: parseTags(formData.get("members")) },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
  revalidatePath(`${MY_CONTRIBUTIONS_PATH}/${contributionId}/tracking`);
  return { error: null, success: true };
}

export type MessagesResult = {
  error: string | null;
  messages?: trackingApi.ContributorMessage[];
};

/** The current user's saved contributor messages (empty for guests). */
export async function fetchContributorMessagesAction(): Promise<
  trackingApi.ContributorMessage[]
> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return [];
  }
  try {
    return await trackingApi.listContributorMessages(token);
  } catch {
    return [];
  }
}

/** Save a reusable contributor message; returns the refreshed list. */
export async function saveContributorMessageAction(
  body: string,
): Promise<MessagesResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    return { error: dict.tracking.errorGeneric };
  }
  const text = body.trim();
  if (!text) {
    return { error: dict.tracking.errorDescriptionRequired };
  }
  try {
    await trackingApi.createContributorMessage(text, token);
    return {
      error: null,
      messages: await trackingApi.listContributorMessages(token),
    };
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
}

/** Delete a saved contributor message; returns the refreshed list. */
export async function deleteContributorMessageAction(
  messageId: string,
): Promise<MessagesResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    return { error: dict.tracking.errorGeneric };
  }
  try {
    await trackingApi.deleteContributorMessage(messageId, token);
    return {
      error: null,
      messages: await trackingApi.listContributorMessages(token),
    };
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
}

/** Append a record to a token's timeline (auth optional). `token` bound. */
export async function addRecordAction(
  trackingToken: string,
  _prevState: TrackingState,
  formData: FormData,
): Promise<TrackingState> {
  const authToken = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.tracking;

  const description = String(formData.get("description") ?? "").trim();
  if (!description) {
    return { error: t.errorDescriptionRequired };
  }
  try {
    await trackingApi.addTrackingRecord(
      trackingToken,
      {
        description,
        tags: parseTags(formData.get("tags")),
        display_anonymous: formData.get("display_anonymous") === "on",
      },
      authToken,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/track/${trackingToken}`);
  return { error: null, success: true };
}

/**
 * Confirm the scanned package as received at its collection center.
 *
 * Offered on the public tracking page because that is where the center
 * actually observes the arrival — often on units the maker never advanced
 * past "claimed"/"prepared". The backend re-checks that the caller is an
 * effective member of the center (or a maintainer/admin), so this is a UX
 * affordance, not the gate (NFR-006).
 */
export async function confirmReceivedAction(
  trackingToken: string,
): Promise<TrackingState> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    redirect(`/login?next=/track/${trackingToken}`);
  }
  try {
    await trackingApi.confirmTrackingReceived(trackingToken, token);
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
  revalidatePath(`/track/${trackingToken}`);
  return { error: null, success: true };
}

/**
 * Correct the scanned Contribution's unit count (maintainer/admin).
 *
 * Offered on the tracking page because that is where the discrepancy is
 * found: the center opens the package and counts 300 pieces against the
 * maker's 283. The backend re-checks the maintainer/admin override and is not
 * bound by the maker's `delivered` edit lock, so this reaches the states where
 * it actually matters. Role is re-verified here too (NFR-006).
 */
export async function adjustQuantityAction(
  trackingToken: string,
  quantity: number,
): Promise<QuantityState> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.tracking;
  if (!token) {
    redirect(`/login?next=/track/${trackingToken}`);
  }
  if (!Number.isInteger(quantity) || quantity < 1) {
    return { error: t.errorInvalidQuantity };
  }
  const user = await getCurrentUser();
  if (user?.role !== "maintainer" && user?.role !== "admin") {
    return { error: t.errorQuantityForbidden };
  }
  let updated;
  try {
    updated = await trackingApi.adjustTrackingQuantity(
      trackingToken,
      quantity,
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/track/${trackingToken}`);
  // Hand back the server's unit count rather than the requested quantity: it
  // is clamped at MAX_TRACKED_UNITS, and the caller uses it to preselect the
  // reprint window.
  return { error: null, success: true, trackedUnits: updated.tracked_units };
}

/** Replace a record's tags (author / owner / admin). `recordId` bound. */
export async function editRecordTagsAction(
  recordId: string,
  revalidate: string,
  _prevState: TrackingState,
  formData: FormData,
): Promise<TrackingState> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  if (!token) {
    redirect("/login");
  }
  try {
    await trackingApi.editRecordTags(
      recordId,
      parseTags(formData.get("tags")),
      token,
    );
  } catch (error) {
    return { error: messageFor(error, dict.tracking) };
  }
  revalidatePath(revalidate);
  return { error: null, success: true };
}
