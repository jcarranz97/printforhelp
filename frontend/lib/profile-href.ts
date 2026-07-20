/**
 * Where a handle's public profile lives — or `null` when it has none.
 *
 * Profiles are served from the root (`/{username}`), so a handle that matches
 * a static top-level route is shadowed by that page: `/admin` is the admin
 * panel, never the bootstrap admin's profile. New accounts cannot take these
 * names (the backend rejects them — see `backend/app/handles.py`), but the
 * system accounts created at bootstrap predate that check, and they comment.
 *
 * Keep this in sync with the top-level segments under `app/`.
 */
const SHADOWED_BY_A_ROUTE = new Set([
  "about",
  "admin",
  "centers",
  "forgot-password",
  "login",
  "logout",
  "my-contributions",
  "parts",
  "register",
  "requests",
  "reset-password",
  "settings",
  "supplies",
  "track",
  "unsubscribe",
]);

/** The profile URL for a handle, or null if no profile page can exist. */
export function profileHref(username: string): string | null {
  return SHADOWED_BY_A_ROUTE.has(username.toLowerCase())
    ? null
    : `/${username}`;
}
