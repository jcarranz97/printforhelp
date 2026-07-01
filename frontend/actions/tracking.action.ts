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

import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as trackingApi from "@/lib/tracking.api";
import type { TrackingVisibility } from "@/lib/tracking.api";

const MY_CONTRIBUTIONS_PATH = "/my-contributions";

export type TrackingState = { error: string | null; success?: boolean };

function messageFor(error: unknown, t: Dictionary["tracking"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "TRACKING_FORBIDDEN":
        return t.errorForbidden;
      case "TRACKING_ALREADY_EXISTS":
        return t.errorAlreadyExists;
      case "RECORD_EDIT_FORBIDDEN":
        return t.errorEditForbidden;
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
