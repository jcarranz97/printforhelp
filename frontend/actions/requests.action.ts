"use server";

/**
 * Server actions for the Requests domain. Creating or closing a campaign
 * requires a session; the backend re-checks effective-requester rights.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { createCollectionCenter } from "@/lib/collection-centers.api";
import * as requestsApi from "@/lib/requests.api";
import type { CreateRequestItem } from "@/lib/requests.api";
import { uploadImage } from "@/lib/uploads.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const REQUESTS_PATH = "/requests";

export type CreateRequestState = { error: string | null };

function messageFor(error: unknown, t: Dictionary["requestForm"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "DUPLICATE_PART":
        return t.errorDuplicatePart;
      case "PART_DISCONTINUED":
        return t.errorPartDiscontinued;
      case "PART_NOT_FOUND":
        return t.errorPartNotFound;
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
 * Resolve the campaign image URL: an attached file is uploaded and its
 * stored URL wins; otherwise the optional pasted URL is the fallback.
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
 * Read the cover image focal point (percent, 0-100 on each axis) the form
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
 * Read the optional preferred drop-off centers. The form submits one hidden
 * `preferred_center_ids` field holding a comma-separated list of center UUIDs.
 */
function parsePreferredCenterIds(formData: FormData): string[] {
  const raw = String(formData.get("preferred_center_ids") ?? "").trim();
  return raw
    ? raw
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean)
    : [];
}

/** Create a campaign with one or more items (FR-038). */
export async function createRequestAction(
  _prevState: CreateRequestState,
  formData: FormData,
): Promise<CreateRequestState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.requestForm;

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/new`);
  }

  const title = String(formData.get("title") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const beneficiary = String(formData.get("beneficiary") ?? "").trim();
  const packagingInstructions = String(
    formData.get("packaging_instructions") ?? "",
  ).trim();
  const imageUrl = String(formData.get("image_url") ?? "").trim();
  const deadline = String(formData.get("deadline") ?? "").trim();
  const preferredCenterIds = parsePreferredCenterIds(formData);
  const focus = parseImageFocus(formData);

  // The client serializes the dynamic item rows into a JSON field.
  let items: CreateRequestItem[] = [];
  try {
    const raw = String(formData.get("items") ?? "[]");
    items = JSON.parse(raw) as CreateRequestItem[];
  } catch {
    items = [];
  }
  items = items.filter((item) => item.resource_id);

  // Items are optional (FR-038): a request may start empty and have parts
  // added later. Only the title is required.
  if (!title) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await requestsApi.createRequest(
      {
        title,
        description: description || undefined,
        beneficiary: beneficiary || undefined,
        packaging_instructions: packagingInstructions || undefined,
        image_url: resolvedImageUrl || undefined,
        image_focus_x: focus.x,
        image_focus_y: focus.y,
        deadline: deadline || undefined,
        preferred_collection_center_ids: preferredCenterIds,
        items,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(REQUESTS_PATH);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(REQUESTS_PATH);
}

export type UpdateRequestState = { error: string | null };

/** Edit campaign metadata (effective requester). `requestId` is bound. */
export async function updateRequestAction(
  requestId: string,
  _prevState: UpdateRequestState,
  formData: FormData,
): Promise<UpdateRequestState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.requestForm;

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  const title = String(formData.get("title") ?? "").trim();
  const description = String(formData.get("description") ?? "").trim();
  const beneficiary = String(formData.get("beneficiary") ?? "").trim();
  const packagingInstructions = String(
    formData.get("packaging_instructions") ?? "",
  ).trim();
  const imageUrl = String(formData.get("image_url") ?? "").trim();
  const deadline = String(formData.get("deadline") ?? "").trim();
  const preferredCenterIds = parsePreferredCenterIds(formData);
  const focus = parseImageFocus(formData);

  if (!title) {
    return { error: t.errorRequired };
  }

  try {
    const resolvedImageUrl = await resolveImageUrl(formData, imageUrl, token);
    await requestsApi.updateRequest(
      requestId,
      {
        title,
        description: description || null,
        beneficiary: beneficiary || null,
        packaging_instructions: packagingInstructions || null,
        image_url: resolvedImageUrl || null,
        image_focus_x: focus.x,
        image_focus_y: focus.y,
        deadline: deadline || null,
        preferred_collection_center_ids: preferredCenterIds,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(REQUESTS_PATH);
  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect(`${REQUESTS_PATH}/${requestId}`);
}

/** Reopen a closed campaign (effective requester). `requestId` is bound. */
export async function reopenRequestAction(
  requestId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.reopenRequest(requestId, token);
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(REQUESTS_PATH);
  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null };
}

/** Close a campaign (effective requester). `requestId` is bound by caller. */
export async function closeRequestAction(
  requestId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.closeRequest(requestId, null, token);
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(REQUESTS_PATH);
  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null };
}

export type UpdateItemState = { error: string | null; success?: boolean };

/** Edit an open item's target quantity (effective requester). IDs bound. */
export async function updateItemAction(
  requestId: string,
  itemId: string,
  _prevState: UpdateItemState,
  formData: FormData,
): Promise<UpdateItemState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.requestForm;

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  const quantityRaw = String(formData.get("quantity") ?? "").trim();
  // Empty quantity means "as many as possible" (null target).
  const quantity = quantityRaw ? Number(quantityRaw) : null;
  if (quantity !== null && (!Number.isInteger(quantity) || quantity < 1)) {
    return { error: t.errorRequired };
  }
  // A `unit` field is present only when the item is a supply; when present,
  // an empty value clears it (back to countable pieces).
  const hasUnit = formData.has("unit");
  const unit = String(formData.get("unit") ?? "").trim();

  try {
    await requestsApi.updateRequestItem(
      requestId,
      itemId,
      hasUnit ? { quantity, unit: unit || null } : { quantity },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null, success: true };
}

export type AddItemState = { error: string | null; success?: boolean };

/** Add a part to an open campaign (effective requester). `requestId` bound. */
export async function addItemAction(
  requestId: string,
  _prevState: AddItemState,
  formData: FormData,
): Promise<AddItemState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.requestForm;

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  const partId = String(formData.get("resource_id") ?? "");
  const quantityRaw = String(formData.get("quantity") ?? "").trim();
  const unit = String(formData.get("unit") ?? "").trim();
  if (!partId) {
    return { error: t.errorRequired };
  }

  try {
    await requestsApi.addRequestItem(
      requestId,
      {
        resource_id: partId,
        quantity: quantityRaw ? Number(quantityRaw) : null,
        unit: unit || null,
      },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null, success: true };
}

export type PrivateCenter = {
  id: string;
  name: string;
  city: string;
  country: string;
  location_url: string | null;
};

export type CreatePrivateCenterState = {
  error: string | null;
  center?: PrivateCenter;
};

/** Register a private, request-specific drop-off location (`listed=false`),
 * owned by the caller, for use in the request's preferred centers. */
export async function createPrivateCenterAction(input: {
  name: string;
  address: string;
  country: string;
  city: string;
  contact: string;
  location_url: string;
  opening_hours: string;
}): Promise<CreatePrivateCenterState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();
  const t = dict.requestForm;

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/new`);
  }

  const name = input.name.trim();
  const address = input.address.trim();
  const country = input.country.trim();
  const city = input.city.trim();
  const contact = input.contact.trim();
  if (!name || !address || !country || !city || !contact) {
    return { error: t.locationErrorRequired };
  }

  try {
    const center = await createCollectionCenter(
      {
        name,
        address,
        country,
        state: "",
        city,
        contact,
        location_url: input.location_url.trim() || undefined,
        opening_hours: input.opening_hours.trim() || undefined,
        listed: false,
      },
      token,
    );
    return {
      error: null,
      center: {
        id: center.id,
        name: center.name,
        city: center.city,
        country: center.country,
        location_url: center.location_url,
      },
    };
  } catch (error) {
    return { error: messageFor(error, t) };
  }
}

export type SetItemDescriptionState = {
  error: string | null;
  success?: boolean;
};

/** Set an item's Markdown description (effective requester). IDs bound. */
export async function setItemDescriptionAction(
  requestId: string,
  itemId: string,
  description: string,
): Promise<SetItemDescriptionState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.updateRequestItem(
      requestId,
      itemId,
      { description: description.trim() || null },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null, success: true };
}

export type SetItemCentersState = { error: string | null; success?: boolean };

/** Set an item's preferred drop-off centers (a subset of the request's).
 * `requestId`/`itemId` are bound by the caller. */
export async function setItemCentersAction(
  requestId: string,
  itemId: string,
  centerIds: string[],
): Promise<SetItemCentersState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.updateRequestItem(
      requestId,
      itemId,
      { preferred_collection_center_ids: centerIds },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null, success: true };
}

/** Close one item without closing the campaign. IDs bound by the caller. */
export async function closeItemAction(
  requestId: string,
  itemId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.closeRequestItem(requestId, itemId, token);
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null };
}

/** Reopen a closed item on an open campaign. IDs bound by the caller. */
export async function reopenItemAction(
  requestId: string,
  itemId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.reopenRequestItem(requestId, itemId, token);
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null };
}

/** Remove an item from an open campaign. IDs bound by the caller. */
export async function removeItemAction(
  requestId: string,
  itemId: string,
): Promise<{ error: string | null }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await requestsApi.removeRequestItem(requestId, itemId, token);
  } catch (error) {
    return { error: messageFor(error, dict.requestForm) };
  }

  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null };
}

// ---------------------------------------------------------------------------
// Moderation (FR-134 / FR-135)
// ---------------------------------------------------------------------------

export type ModerationState = { error: string | null; success?: boolean };

/** Map the moderation error codes onto localized copy. */
function moderationMessageFor(
  error: unknown,
  t: Dictionary["moderation"],
): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "REQUEST_NEEDS_ITEM":
        return t.errorNeedsItem;
      case "REQUEST_NOT_SUBMITTABLE":
        return t.errorNotSubmittable;
      case "REQUEST_NOT_PENDING":
        return t.errorNotPending;
      case "REQUEST_NOT_APPROVED":
        return t.errorNotApproved;
      case "NOT_EFFECTIVE_REQUESTER":
        return t.errorForbidden;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/** Run a moderation call with the session token and refresh the affected pages. */
async function moderate(
  requestId: string,
  call: (token: string) => Promise<unknown>,
): Promise<ModerationState> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const { dict } = await getServerI18n();

  if (!token) {
    redirect(`/login?next=${REQUESTS_PATH}/${requestId}`);
  }

  try {
    await call(token);
  } catch (error) {
    return { error: moderationMessageFor(error, dict.moderation) };
  }

  // A verdict changes both what the directory lists and what the campaign page
  // shows (the banner, and whether it is public at all).
  revalidatePath(REQUESTS_PATH);
  revalidatePath(`${REQUESTS_PATH}/${requestId}`);
  return { error: null, success: true };
}

/** Author sends their draft to the review queue. */
export async function submitRequestAction(
  requestId: string,
): Promise<ModerationState> {
  return moderate(requestId, (token) =>
    requestsApi.submitRequest(requestId, token),
  );
}

/** Maintainer publishes a campaign awaiting review. */
export async function approveRequestAction(
  requestId: string,
): Promise<ModerationState> {
  return moderate(requestId, (token) =>
    requestsApi.approveRequest(requestId, token),
  );
}

/** Maintainer turns a campaign down; it is never published. */
export async function rejectRequestAction(
  requestId: string,
): Promise<ModerationState> {
  return moderate(requestId, (token) =>
    requestsApi.rejectRequest(requestId, token),
  );
}

/** Take a published campaign back down and re-queue it for review (FR-135). */
export async function unpublishRequestAction(
  requestId: string,
  _prevState: ModerationState,
): Promise<ModerationState> {
  return moderate(requestId, (token) =>
    requestsApi.unpublishRequest(requestId, token),
  );
}
