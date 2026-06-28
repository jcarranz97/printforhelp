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
