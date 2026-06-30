"use server";

/**
 * Server actions for site notices. Admin/maintainer mutations re-verify the
 * caller's role server-side (NFR-006); the entity-request action is open to
 * any logged-in user and lets the backend enforce ownership. Each action
 * revalidates the affected path so the server-rendered banners refresh.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { fetchMe } from "@/lib/auth.api";
import * as noticesApi from "@/lib/notices.api";
import type {
  CreateNoticePayload,
  RequestNoticePayload,
  UpdateNoticePayload,
} from "@/lib/notices.api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";

const ADMIN_NOTICES_PATH = "/admin/notices";

export type NoticeActionResult = { error: string | null };

/** Resolve the caller's token, redirecting unless they are maintainer/admin. */
async function requireMaintainerToken(): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    redirect(`/login?next=${ADMIN_NOTICES_PATH}`);
  }
  const me = await fetchMe(token);
  if (!me || (me.role !== "maintainer" && me.role !== "admin")) {
    redirect("/");
  }
  return token;
}

/** Translate a backend error into a localized, user-facing message. */
function messageFor(error: unknown, t: Dictionary["notices"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NOT_ENTITY_OWNER":
        return t.errorNotOwner;
      case "NOTICE_NOT_FOUND":
        return t.errorNotFound;
      case "NOTICE_NOT_PENDING":
        return t.errorNotPending;
      case "TRANSLATIONS_REQUIRED":
        return t.errorTranslationsRequired;
      case "DUPLICATE_LANGUAGE":
        return t.errorDuplicateLanguage;
      case "INVALID_NOTICE_MODE":
        return t.errorInvalidMode;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

/** Create an approved page banner (maintainer/admin). */
export async function createPageNoticeAction(
  payload: CreateNoticePayload,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.createNotice(token, payload);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  revalidatePath("/", "layout");
  return { error: null };
}

/** Request a notice on an entity the caller owns (any logged-in user). */
export async function requestNoticeAction(
  revalidate: string,
  payload: RequestNoticePayload,
): Promise<NoticeActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.notices;
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { error: t.errorAuth };
  }
  try {
    await noticesApi.requestNotice(token, payload);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(revalidate);
  return { error: null };
}

/** Approve a pending notice (maintainer/admin). */
export async function approveNoticeAction(
  id: string,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.approveNotice(token, id);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  revalidatePath("/", "layout");
  return { error: null };
}

/** Decline a pending notice (maintainer/admin). */
export async function declineNoticeAction(
  id: string,
  reason?: string,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.declineNotice(token, id, reason);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  return { error: null };
}

/** Edit a notice's severity, scopes and/or translations (maintainer/admin). */
export async function updateNoticeAction(
  id: string,
  payload: UpdateNoticePayload,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.updateNotice(token, id, payload);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  // Entity notices live on dynamic detail pages; revalidate everything under
  // the root layout so those banners refresh too.
  revalidatePath("/", "layout");
  return { error: null };
}

/** Enable or disable a notice (maintainer/admin). */
export async function toggleNoticeAction(
  id: string,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.toggleNotice(token, id);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  revalidatePath("/", "layout");
  return { error: null };
}

/** Archive a notice (maintainer/admin). */
export async function deleteNoticeAction(
  id: string,
): Promise<NoticeActionResult> {
  const token = await requireMaintainerToken();
  const { dict } = await getServerI18n();
  try {
    await noticesApi.deleteNotice(token, id);
  } catch (error) {
    return { error: messageFor(error, dict.notices) };
  }
  revalidatePath(ADMIN_NOTICES_PATH);
  revalidatePath("/", "layout");
  return { error: null };
}
