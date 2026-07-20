"use server";

/** Server actions backing the profile timeline (paging + moderator controls). */

import { getSessionToken } from "@/actions/auth.action";
import { getPublicActivity, setRenameHidden } from "@/lib/users.api";
import type { ProfileActivityPage } from "@/lib/users.api";

/**
 * Load an older page of a user's contribution timeline.
 *
 * The read is public, but it still goes through a server action so the browser
 * talks to our own origin rather than the API directly — matching how every
 * other fetch in the app works. The session token is forwarded so a
 * maintainer/admin keeps seeing hidden renames while paging. Returns null on
 * failure so the button can show a retry instead of throwing away the
 * already-loaded months.
 */
export async function loadMoreActivityAction(
  username: string,
  before: string,
  year: number | null,
): Promise<ProfileActivityPage | null> {
  try {
    const token = await getSessionToken();
    return await getPublicActivity(
      username,
      before,
      year ?? undefined,
      token ?? undefined,
    );
  } catch {
    return null;
  }
}

/**
 * Hide or reveal a username-change entry on a public profile timeline. The
 * maintainer/admin role is enforced server-side; this returns whether the
 * toggle succeeded so the timeline can update in place.
 */
export async function setRenameHiddenAction(
  changeId: string,
  hidden: boolean,
): Promise<boolean> {
  const token = await getSessionToken();
  if (!token) {
    return false;
  }
  try {
    await setRenameHidden(token, changeId, hidden);
    return true;
  } catch {
    return false;
  }
}
