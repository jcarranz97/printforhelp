/** Raw API calls for site notices (page banners + per-entity notices). */

import type { Locale } from "@/i18n/config";
import { apiBaseUrl, toApiError } from "@/lib/api";

export type NoticeSeverity = "info" | "success" | "warning" | "critical";
export type NoticeStatus = "pending" | "approved" | "declined";
export type NoticeTargetType = "resource" | "collection_center" | "request";
export type PageScope =
  | "all"
  | "home"
  | "centers"
  | "requests"
  | "parts"
  | "my_contributions"
  | "about";

/** Language a notice falls back to when the active locale has no copy. */
export const DEFAULT_NOTICE_LANGUAGE = "en";

export type NoticeTranslation = {
  language: string;
  title: string | null;
  message: string;
  action_label: string | null;
  action_url: string | null;
};

export type Notice = {
  id: string;
  severity: NoticeSeverity;
  scopes: string[];
  target_type: string | null;
  target_id: string | null;
  status: NoticeStatus;
  enabled: boolean;
  decline_reason: string | null;
  requested_by_id: string;
  approved_by_id: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
  translations: NoticeTranslation[];
};

export type NoticeTranslationInput = {
  language: string;
  title?: string | null;
  message: string;
  action_label?: string | null;
  action_url?: string | null;
};

export type CreateNoticePayload = {
  severity: NoticeSeverity;
  scopes?: PageScope[];
  target_type?: NoticeTargetType;
  target_id?: string;
  translations: NoticeTranslationInput[];
};

export type RequestNoticePayload = {
  severity: NoticeSeverity;
  target_type: NoticeTargetType;
  target_id: string;
  translations: NoticeTranslationInput[];
};

export type UpdateNoticePayload = {
  severity?: NoticeSeverity;
  /** Page-mode only; the backend rejects scopes on an entity notice. */
  scopes?: PageScope[];
  translations?: NoticeTranslationInput[];
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJson(res: Response): Promise<Notice> {
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Notice;
}

/** All approved, enabled page banners (entity notices excluded). Public. */
export async function listPageNotices(): Promise<Notice[]> {
  const res = await fetch(`${apiBaseUrl()}/notices`, { cache: "no-store" });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Notice[];
}

/** Approved, enabled notices attached to one entity. Public. */
export async function listEntityNotices(
  targetType: NoticeTargetType,
  targetId: string,
): Promise<Notice[]> {
  const params = new URLSearchParams({
    target_type: targetType,
    target_id: targetId,
  });
  const res = await fetch(`${apiBaseUrl()}/notices?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Notice[];
}

/** Every active notice for the moderation tab (maintainer/admin). */
export async function listManageNotices(
  token: string,
  status?: NoticeStatus,
): Promise<Notice[]> {
  const query = status ? `?status=${status}` : "";
  const res = await fetch(`${apiBaseUrl()}/notices/manage${query}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Notice[];
}

/** Create an approved notice directly (maintainer/admin). */
export async function createNotice(
  token: string,
  payload: CreateNoticePayload,
): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    }),
  );
}

/** Request an entity notice (owner -> pending, maintainer -> approved). */
export async function requestNotice(
  token: string,
  payload: RequestNoticePayload,
): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/request`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    }),
  );
}

/** Approve a pending notice (maintainer/admin). */
export async function approveNotice(
  token: string,
  id: string,
): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/${id}/approve`, {
      method: "POST",
      headers: authHeaders(token),
      cache: "no-store",
    }),
  );
}

/** Decline a pending notice (maintainer/admin). */
export async function declineNotice(
  token: string,
  id: string,
  reason?: string,
): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/${id}/decline`, {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ reason: reason ?? null }),
      cache: "no-store",
    }),
  );
}

/** Enable or disable a notice (maintainer/admin). */
export async function toggleNotice(token: string, id: string): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/${id}/toggle`, {
      method: "POST",
      headers: authHeaders(token),
      cache: "no-store",
    }),
  );
}

/** Edit a notice's severity, scopes and/or translations (maintainer/admin). */
export async function updateNotice(
  token: string,
  id: string,
  payload: UpdateNoticePayload,
): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/${id}`, {
      method: "PATCH",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    }),
  );
}

/** Archive a notice (maintainer, or the requester of a pending one). */
export async function deleteNotice(token: string, id: string): Promise<Notice> {
  return readJson(
    await fetch(`${apiBaseUrl()}/notices/${id}`, {
      method: "DELETE",
      headers: authHeaders(token),
      cache: "no-store",
    }),
  );
}

/**
 * Pick the best translation for the active locale: an exact match, else
 * English, else the first available. Returns null only if there are none.
 */
export function resolveTranslation(
  notice: Notice,
  locale: Locale,
): NoticeTranslation | null {
  const byLang = (lang: string) =>
    notice.translations.find((t) => t.language === lang);
  return (
    byLang(locale) ??
    byLang(DEFAULT_NOTICE_LANGUAGE) ??
    notice.translations[0] ??
    null
  );
}
