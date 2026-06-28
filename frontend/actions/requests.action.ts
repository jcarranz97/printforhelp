"use server";

/**
 * Server actions for the Requests domain. Creating or closing a campaign
 * requires a session; the backend re-checks effective-requester rights.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import * as requestsApi from "@/lib/requests.api";
import type { CreateRequestItem } from "@/lib/requests.api";
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
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
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
  const deadline = String(formData.get("deadline") ?? "").trim();

  // The client serializes the dynamic item rows into a JSON field.
  let items: CreateRequestItem[] = [];
  try {
    const raw = String(formData.get("items") ?? "[]");
    items = JSON.parse(raw) as CreateRequestItem[];
  } catch {
    items = [];
  }
  items = items.filter((item) => item.part_id);

  if (!title || items.length === 0) {
    return { error: t.errorRequired };
  }

  try {
    await requestsApi.createRequest(
      {
        title,
        description: description || undefined,
        deadline: deadline || undefined,
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
  const deadline = String(formData.get("deadline") ?? "").trim();

  if (!title) {
    return { error: t.errorRequired };
  }

  try {
    await requestsApi.updateRequest(
      requestId,
      {
        title,
        description: description || null,
        deadline: deadline || null,
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

  try {
    await requestsApi.updateRequestItem(requestId, itemId, { quantity }, token);
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

  const partId = String(formData.get("part_id") ?? "");
  const quantityRaw = String(formData.get("quantity") ?? "").trim();
  if (!partId) {
    return { error: t.errorRequired };
  }

  try {
    await requestsApi.addRequestItem(
      requestId,
      { part_id: partId, quantity: quantityRaw ? Number(quantityRaw) : null },
      token,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
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
