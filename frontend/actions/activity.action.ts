"use server";

/** Server action backing the profile timeline's "Show more activity" button. */

import { getPublicActivity } from "@/lib/users.api";
import type { ProfileActivityPage } from "@/lib/users.api";

/**
 * Load an older page of a user's contribution timeline.
 *
 * The read is public, but it still goes through a server action so the browser
 * talks to our own origin rather than the API directly — matching how every
 * other fetch in the app works. Returns null on failure so the button can show
 * a retry instead of throwing away the already-loaded months.
 */
export async function loadMoreActivityAction(
  username: string,
  before: string,
  year: number | null,
): Promise<ProfileActivityPage | null> {
  try {
    return await getPublicActivity(username, before, year ?? undefined);
  } catch {
    return null;
  }
}
