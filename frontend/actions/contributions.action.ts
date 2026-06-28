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
const MY_PRINTS_PATH = "/my-prints";

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
  const centerId = String(formData.get("collection_center_id") ?? "");
  const quantity = Number(formData.get("quantity") ?? 0);
  const notes = String(formData.get("notes") ?? "").trim();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }
  // The drop-off center is optional at claim time (it can be set later).
  if (!requestItemId || !Number.isInteger(quantity) || quantity < 1) {
    return { error: t.errorRequired };
  }

  try {
    await contributionsApi.createContribution(
      {
        request_item_id: requestItemId,
        collection_center_id: centerId || undefined,
        quantity,
        notes: notes || undefined,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  if (requestId) {
    revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  }
  revalidatePath(MY_PRINTS_PATH);
  return { error: null, success: true };
}

/**
 * Advance a Contribution one step (mark printed/delivered, confirm
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
    redirect(`/login?next=${MY_PRINTS_PATH}`);
  }

  try {
    await contributionsApi.advanceContribution(contributionId, action, token);
  } catch (error) {
    return { error: messageFor(error, dict.contributions) };
  }

  revalidatePath(MY_PRINTS_PATH);
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
    redirect(`/login?next=${MY_PRINTS_PATH}`);
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

  revalidatePath(MY_PRINTS_PATH);
  return { error: null, success: true };
}
