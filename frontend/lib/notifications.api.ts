/**
 * Raw API calls for in-app notifications and watch subscriptions
 * (server-side only). Every call is authenticated: a user only ever
 * touches their own notifications and subscriptions.
 */

import { apiBaseUrl, toApiError } from "@/lib/api";
import type { ActorSummary, EntityType } from "@/lib/feed.api";

export type NotificationReason = "mention" | "watch";

export type Notification = {
  id: string;
  entity_type: EntityType;
  entity_id: string;
  actor: ActorSummary;
  reason: NotificationReason;
  event: string;
  comment_id: string | null;
  title: string;
  link: string;
  /** URL fragment (e.g. `record-<id>`) to deep-link to and highlight the
   * exact item on the target page; null for whole-entity notifications. */
  anchor: string | null;
  read_at: string | null;
  created_at: string;
};

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** List the current user's notifications, newest first. */
export async function listNotifications(
  token: string,
  opts: { unreadOnly?: boolean; limit?: number } = {},
): Promise<Notification[]> {
  const params = new URLSearchParams();
  if (opts.unreadOnly) {
    params.set("unread_only", "true");
  }
  if (opts.limit) {
    params.set("limit", String(opts.limit));
  }
  const query = params.toString();
  const res = await fetch(
    `${apiBaseUrl()}/notifications${query ? `?${query}` : ""}`,
    { headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Notification[];
}

/** The current user's unread notification count (for the badge). */
export async function unreadCount(token: string): Promise<number> {
  const res = await fetch(`${apiBaseUrl()}/notifications/unread-count`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  const data = (await res.json()) as { count: number };
  return data.count;
}

/** Mark specific notifications (or all unread) as read. */
export async function markRead(
  token: string,
  payload: { ids?: string[]; all?: boolean },
): Promise<number> {
  const res = await fetch(`${apiBaseUrl()}/notifications/read`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  const data = (await res.json()) as { updated: number };
  return data.updated;
}

/** Whether the current user is watching an entity. */
export async function getWatch(
  token: string,
  entityType: EntityType,
  entityId: string,
): Promise<boolean> {
  const res = await fetch(`${apiBaseUrl()}/watches/${entityType}/${entityId}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  const data = (await res.json()) as { watching: boolean };
  return data.watching;
}

/** Subscribe the current user to an entity. */
export async function watch(
  token: string,
  entityType: EntityType,
  entityId: string,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/watches`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
    cache: "no-store",
  });
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}

/** Unsubscribe the current user from an entity. */
export async function unwatch(
  token: string,
  entityType: EntityType,
  entityId: string,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/watches/${entityType}/${entityId}`, {
    method: "DELETE",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}
