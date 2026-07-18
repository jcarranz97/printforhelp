/**
 * Raw API calls for notification preferences and the no-login unsubscribe
 * flow (server-side only). The preference calls are authenticated (a user
 * only touches their own); the unsubscribe calls carry a signed token
 * instead, so they work straight from an email link without a session.
 */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type NotificationCategory =
  | "mention"
  | "comment"
  | "status_change"
  | "item_added"
  | "tracking_update"
  | "request_reviewed"
  | "review_queue"
  | "reaction";

export type NotificationPreference = {
  category: NotificationCategory;
  in_app_enabled: boolean;
  email_enabled: boolean;
};

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** The current user's per-category channel choices (defaults filled in). */
export async function getPreferences(
  token: string,
): Promise<NotificationPreference[]> {
  const res = await fetch(`${apiBaseUrl()}/notifications/preferences`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as NotificationPreference[];
}

/** Set both channels for one category; returns the updated row. */
export async function updatePreference(
  token: string,
  category: NotificationCategory,
  channels: { in_app_enabled: boolean; email_enabled: boolean },
): Promise<NotificationPreference> {
  const res = await fetch(
    `${apiBaseUrl()}/notifications/preferences/${category}`,
    {
      method: "PUT",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      cache: "no-store",
      body: JSON.stringify(channels),
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as NotificationPreference;
}

/** Describe what a signed unsubscribe token will do (for the confirm page). */
export async function previewUnsubscribe(token: string): Promise<string> {
  const res = await fetch(
    `${apiBaseUrl()}/notifications/unsubscribe/preview?token=${encodeURIComponent(
      token,
    )}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return ((await res.json()) as { description: string }).description;
}

/** Apply a signed unsubscribe token; returns the confirmation message. */
export async function confirmUnsubscribe(token: string): Promise<string> {
  const res = await fetch(`${apiBaseUrl()}/notifications/unsubscribe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ token }),
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return ((await res.json()) as { message: string }).message;
}
