"use server";

/**
 * Server actions for the Contribution lifecycle. Claiming and advancing
 * a Contribution require a session; the backend enforces maker / center
 * membership rules (FR-050/053/056).
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as contributionsApi from "@/lib/contributions.api";
import type { ContributionAction } from "@/lib/contributions.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const REQUESTS_PATH = "/requests";
const MY_CONTRIBUTIONS_PATH = "/my-contributions";

export type ClaimState = { error: string | null; success?: boolean };

function messageFor(error: unknown, t: Dictionary["contributions"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "CENTER_NOT_AVAILABLE":
        return t.errorCenterUnavailable;
      case "CENTER_REQUIRED":
        return t.errorCenterRequired;
      case "REQUEST_ITEM_NOT_OPEN":
        return t.errorItemClosed;
      case "INVALID_TRANSITION":
        return t.errorInvalidTransition;
      case "NOT_THE_MAKER":
        return t.errorNotMaker;
      case "NOT_RECEIVER":
        return t.errorNotReceiver;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/** Claim a quantity of a RequestItem at a Collection Center (FR-050). */
export async function claimAction(
  _prevState: ClaimState,
  formData: FormData,
): Promise<ClaimState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.contributions;

  const requestItemId = String(formData.get("request_item_id") ?? "");
  const requestId = String(formData.get("request_id") ?? "");
  const itemNumber = String(formData.get("item_number") ?? "");
  const quantity = Number(formData.get("quantity") ?? 0);

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }
  // The drop-off center is not asked for at claim time — the maker assigns it
  // later from "My Contributions", before marking the contribution delivered.
  if (!requestItemId || !Number.isInteger(quantity) || quantity < 1) {
    return { error: t.errorRequired };
  }

  try {
    await contributionsApi.createContribution(
      {
        request_item_id: requestItemId,
        quantity,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  if (requestId) {
    revalidatePath(`${REQUESTS_PATH}/${requestId}`);
    // Also refresh the item's own page (its commitments list) — addressed by
    // its per-request number — when the claim was submitted from there.
    if (itemNumber) {
      revalidatePath(`${REQUESTS_PATH}/${requestId}/items/${itemNumber}`);
    }
  }
  revalidatePath(MY_CONTRIBUTIONS_PATH);
  return { error: null, success: true };
}

/**
 * Advance a Contribution one step (mark prepared/delivered, confirm
 * received, or release). `contributionId` and `action` are bound by the
 * caller; `requestId` (optional) is revalidated when supplied.
 */
export async function advanceContributionAction(
  contributionId: string,
  action: ContributionAction,
  requestId: string | null,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${MY_CONTRIBUTIONS_PATH}`);
  }

  try {
    await contributionsApi.advanceContribution(contributionId, action, token);
  } catch (error) {
    return { error: messageFor(error, dict.contributions) };
  }

  revalidatePath(MY_CONTRIBUTIONS_PATH);
  if (requestId) {
    revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  }
  return { error: null };
}

export type SetCenterState = { error: string | null; success?: boolean };

/** Assign a drop-off center to a claimed/printed Contribution. ID bound. */
export async function setContributionCenterAction(
  contributionId: string,
  _prevState: SetCenterState,
  formData: FormData,
): Promise<SetCenterState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.contributions;

  if (!token) {
    redirect(`/login?next=${MY_CONTRIBUTIONS_PATH}`);
  }

  const centerId = String(formData.get("collection_center_id") ?? "");
  if (!centerId) {
    return { error: t.errorRequired };
  }

  try {
    await contributionsApi.updateContribution(
      contributionId,
      { collection_center_id: centerId },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(MY_CONTRIBUTIONS_PATH);
  return { error: null, success: true };
}

export type SetTagsState = { error: string | null; success?: boolean };

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

/** Set the maker's personal tags on their own Contribution. ID bound. */
export async function setContributionTagsAction(
  contributionId: string,
  _prevState: SetTagsState,
  formData: FormData,
): Promise<SetTagsState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.contributions;

  if (!token) {
    redirect(`/login?next=${MY_CONTRIBUTIONS_PATH}`);
  }

  try {
    await contributionsApi.updateContribution(
      contributionId,
      { tags: parseTags(formData.get("tags")) },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(MY_CONTRIBUTIONS_PATH);
  return { error: null, success: true };
}
