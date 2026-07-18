"use server";

/**
 * Server actions for the notification preference center and the no-login
 * email-unsubscribe flow. The preference actions read the auth cookie and
 * forward the token (the real authorization boundary, NFR-006); the
 * unsubscribe actions take a signed token straight from an email link and
 * need no session.
 */

import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import * as prefsApi from "@/lib/notification-prefs.api";
import type {
  NotificationCategory,
  NotificationPreference,
} from "@/lib/notification-prefs.api";

async function readToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

/** Fetch the current user's preferences (empty for guests). */
export async function fetchPreferencesAction(): Promise<
  NotificationPreference[]
> {
  const token = await readToken();
  if (!token) {
    return [];
  }
  return prefsApi.getPreferences(token);
}

/** Update one category's channels; returns the updated row, or null on error. */
export async function updatePreferenceAction(
  category: NotificationCategory,
  channels: { in_app_enabled: boolean; email_enabled: boolean },
): Promise<NotificationPreference | null> {
  const token = await readToken();
  if (!token) {
    return null;
  }
  try {
    return await prefsApi.updatePreference(token, category, channels);
  } catch {
    return null;
  }
}

/** Describe what an unsubscribe token will do; null if the token is invalid. */
export async function previewUnsubscribeAction(
  token: string,
): Promise<string | null> {
  try {
    return await prefsApi.previewUnsubscribe(token);
  } catch {
    return null;
  }
}

/** Apply an unsubscribe token; returns the confirmation message or null. */
export async function confirmUnsubscribeAction(
  token: string,
): Promise<string | null> {
  try {
    return await prefsApi.confirmUnsubscribe(token);
  } catch {
    return null;
  }
}
