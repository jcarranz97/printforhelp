"use server";

/**
 * Server actions for in-app notifications, watch subscriptions, and the
 * @mention typeahead. These read the auth cookie (server-only) and
 * forward the token to the backend (the real authorization boundary,
 * NFR-006). Client components call them; they never touch the cookie or
 * the backend directly.
 */

import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import type { EntityType } from "@/lib/feed.api";
import * as notificationsApi from "@/lib/notifications.api";
import type { Notification } from "@/lib/notifications.api";
import { searchUsers, type UserSearchResult } from "@/lib/users.api";

async function readToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

/** Fetch the current user's notifications (empty for guests). */
export async function fetchNotificationsAction(
  opts: { unreadOnly?: boolean; limit?: number } = {},
): Promise<Notification[]> {
  const token = await readToken();
  if (!token) {
    return [];
  }
  try {
    return await notificationsApi.listNotifications(token, opts);
  } catch {
    return [];
  }
}

/** Fetch the current user's unread count (0 for guests). */
export async function fetchUnreadCountAction(): Promise<number> {
  const token = await readToken();
  if (!token) {
    return 0;
  }
  try {
    return await notificationsApi.unreadCount(token);
  } catch {
    return 0;
  }
}

/** Mark specific notifications (or all) as read; returns the new unread count. */
export async function markReadAction(payload: {
  ids?: string[];
  all?: boolean;
}): Promise<number> {
  const token = await readToken();
  if (!token) {
    return 0;
  }
  try {
    await notificationsApi.markRead(token, payload);
    return await notificationsApi.unreadCount(token);
  } catch {
    return 0;
  }
}

/** Whether the current user is watching an entity (false for guests). */
export async function fetchWatchStateAction(
  entityType: EntityType,
  entityId: string,
): Promise<boolean> {
  const token = await readToken();
  if (!token) {
    return false;
  }
  try {
    return await notificationsApi.getWatch(token, entityType, entityId);
  } catch {
    return false;
  }
}

export type ToggleWatchResult = { watching: boolean; error: boolean };

/** Toggle a watch subscription; returns the resulting state. */
export async function toggleWatchAction(
  entityType: EntityType,
  entityId: string,
  currentlyWatching: boolean,
): Promise<ToggleWatchResult> {
  const token = await readToken();
  if (!token) {
    return { watching: currentlyWatching, error: true };
  }
  try {
    if (currentlyWatching) {
      await notificationsApi.unwatch(token, entityType, entityId);
      return { watching: false, error: false };
    }
    await notificationsApi.watch(token, entityType, entityId);
    return { watching: true, error: false };
  } catch {
    return { watching: currentlyWatching, error: true };
  }
}

/** Typeahead search for the @mention autocomplete (empty for guests). */
export async function searchUsersAction(
  query: string,
): Promise<UserSearchResult[]> {
  const token = await readToken();
  if (!token) {
    return [];
  }
  try {
    return await searchUsers(token, query);
  } catch {
    return [];
  }
}
