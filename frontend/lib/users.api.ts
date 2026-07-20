/** Raw API calls for admin user management (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";
import type { CurrentUser, Locale, UserRole } from "@/lib/auth.api";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

export type CreateUserPayload = {
  username: string;
  password: string;
  role: UserRole;
  preferred_locale?: Locale;
};

export type UserSearchResult = {
  id: string;
  username: string;
  full_name: string | null;
};

/** The maker actions shown on the profile's contribution timeline. */
export type ProfileActivityKind =
  | "claimed"
  | "prepared"
  | "delivered"
  /** A profile event, not a contribution: the user renamed their handle. */
  | "renamed";

/** One project line inside a timeline entry (rendered as a labelled bar). */
export type ProfileActivityItem = {
  request_id: string;
  request_title: string;
  item_number: number;
  resource_name: string;
  quantity: number;
  unit: string | null;
};

/** One grouped action on the timeline (e.g. all prints in a month). */
export type ProfileActivityEntry = {
  kind: ProfileActivityKind;
  occurred_at: string;
  total_quantity: number;
  request_count: number;
  /** Per-project breakdown; only populated for `prepared`. */
  items: ProfileActivityItem[];
  /** Set when the group belongs to a single campaign, so it can be named. */
  single_request_title: string | null;
  /** Unit shared by the whole group (null = countable pieces / mixed). */
  unit: string | null;
  /** Only for `renamed`: the handles before and after the change. */
  renamed_from: string | null;
  renamed_to: string | null;
  /**
   * Only for `renamed`, and only populated for maintainer/admin viewers: the
   * change's id (targets it for hiding) and whether it is currently hidden.
   * Null for everyone else — regular viewers never see hidden renames.
   */
  rename_id: string | null;
  rename_hidden: boolean;
};

/** A month of timeline entries, newest month first. */
export type ProfileActivityMonth = {
  year: number;
  month: number;
  /**
   * Distinct commitments the month touched. The stage entries are a history
   * and overlap (one commitment claimed *and* printed shows in both), so this
   * is deduplicated.
   */
  contributions_count: number;
  entries: ProfileActivityEntry[];
};

/** One day of the contribution calendar; only active days are sent. */
export type ProfileContributionDay = {
  /** Plain `YYYY-MM-DD` (UTC) — parse as UTC to avoid shifting the square. */
  date: string;
  count: number;
};

/** One page of the timeline plus the cursor for the next (older) one. */
export type ProfileActivityPage = {
  months: ProfileActivityMonth[];
  /** Pass back as `before` to load the next page; null when done. */
  next_before: string | null;
  has_more: boolean;
};

/** The identity half of a public profile — everything a visitor may see. */
export type PublicProfileUser = {
  id: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  avatar_crop_x: number;
  avatar_crop_y: number;
  avatar_crop_w: number;
  avatar_crop_h: number;
  bio: string | null;
  created_at: string;
};

/** A user's public profile (email-free) plus the projects they collaborate on. */
export type PublicProfile = {
  user: PublicProfileUser;
  /** The calendar year shown, or null for the default "last 12 months". */
  selected_year: number | null;
  /** Years the user has activity in, newest first (drives the selector). */
  available_years: number[];
  contributions_total: number;
  contribution_days: ProfileContributionDay[];
  activity: ProfileActivityPage;
};

/** Fields the account owner can edit on their own public profile. */
/** Name + bio; the avatar is saved separately (see {@link AvatarUpdatePayload}). */
export type ProfileUpdatePayload = {
  full_name: string | null;
  bio: string | null;
};

/** The profile picture and the crop shown in it. Null URL removes the photo. */
export type AvatarUpdatePayload = {
  avatar_url: string | null;
  avatar_crop_x: number;
  avatar_crop_y: number;
  avatar_crop_w: number;
  avatar_crop_h: number;
};

/**
 * Fetch a user's public profile by handle. Returns null on 404 so the page can
 * render `notFound()`; other failures throw.
 *
 * The read is public, but passing a maintainer/admin `token` reveals renames a
 * moderator has hidden (so they can reveal them again) — the backend is the
 * authority on that, keying off the bearer token, not a query flag.
 */
export async function getPublicProfile(
  username: string,
  year?: number,
  token?: string,
): Promise<PublicProfile | null> {
  const query = year ? `?year=${year}` : "";
  const res = await fetch(
    `${apiBaseUrl()}/users/${encodeURIComponent(username)}/profile${query}`,
    { cache: "no-store", headers: token ? authHeaders(token) : undefined },
  );
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as PublicProfile;
}

/**
 * Fetch an older page of a user's contribution timeline. Pass the previous
 * page's `next_before` as `before`. A maintainer/admin `token` also reveals
 * hidden renames (see {@link getPublicProfile}).
 */
export async function getPublicActivity(
  username: string,
  before: string,
  year?: number,
  token?: string,
): Promise<ProfileActivityPage> {
  const params = new URLSearchParams({ before });
  if (year) {
    params.set("year", String(year));
  }
  const res = await fetch(
    `${apiBaseUrl()}/users/${encodeURIComponent(username)}/activity?${params}`,
    { cache: "no-store", headers: token ? authHeaders(token) : undefined },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ProfileActivityPage;
}

/**
 * Hide or reveal a username-change entry on the public timeline
 * (maintainer/admin only — enforced server-side).
 */
export async function setRenameHidden(
  token: string,
  changeId: string,
  hidden: boolean,
): Promise<{ id: string; hidden: boolean }> {
  const res = await fetch(
    `${apiBaseUrl()}/users/username-changes/${changeId}/visibility`,
    {
      method: "PUT",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ hidden }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as { id: string; hidden: boolean };
}

/** Update the caller's own name and bio. */
export async function updateMyProfile(
  token: string,
  payload: ProfileUpdatePayload,
): Promise<CurrentUser> {
  return putMe(token, "/users/me", payload);
}

/** Change the caller's public handle (rate-limited server-side). */
export async function changeUsername(
  token: string,
  username: string,
): Promise<CurrentUser> {
  return putMe(token, "/users/me/username", { username });
}

/** Set or clear the caller's profile picture and its crop. */
export async function updateMyAvatar(
  token: string,
  payload: AvatarUpdatePayload,
): Promise<CurrentUser> {
  return putMe(token, "/users/me/avatar", payload);
}

async function putMe(
  token: string,
  path: string,
  payload: ProfileUpdatePayload | AvatarUpdatePayload | { username: string },
): Promise<CurrentUser> {
  const res = await fetch(`${apiBaseUrl()}${path}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}

/** Set one of the caller's own self-assignable flags (e.g. `maker`). */
export async function setOwnFlag(
  token: string,
  key: string,
  value: boolean,
): Promise<Record<string, boolean>> {
  const res = await fetch(`${apiBaseUrl()}/users/me/flags/${key}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ value }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return ((await res.json()) as { flags: Record<string, boolean> }).flags;
}

/** Persist the caller's preferred locale (drives UI + email language). */
export async function setPreferredLocale(
  token: string,
  locale: Locale,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/users/me/locale`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ locale }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Typeahead search for @mention autocomplete (any logged-in user). */
export async function searchUsers(
  token: string,
  query: string,
  limit = 8,
): Promise<UserSearchResult[]> {
  const params = new URLSearchParams({ q: query, limit: String(limit) });
  const res = await fetch(`${apiBaseUrl()}/users/search?${params.toString()}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as UserSearchResult[];
}

/** List all users (admin only). */
export async function listUsers(token: string): Promise<CurrentUser[]> {
  const res = await fetch(`${apiBaseUrl()}/users`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser[];
}

/** Provision a new account (admin only). */
export async function createUser(
  token: string,
  payload: CreateUserPayload,
): Promise<CurrentUser> {
  const res = await fetch(`${apiBaseUrl()}/users`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}

/** Change a user's role (admin only). */
export async function updateUserRole(
  token: string,
  userId: string,
  role: UserRole,
): Promise<CurrentUser> {
  const res = await fetch(`${apiBaseUrl()}/users/${userId}/role`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}

/** Set a new password for a user (admin only). */
export async function resetUserPassword(
  token: string,
  userId: string,
  newPassword: string,
): Promise<CurrentUser> {
  const res = await fetch(`${apiBaseUrl()}/users/${userId}/password`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}

/** Activate or deactivate a user (admin only). */
export async function setUserActive(
  token: string,
  userId: string,
  active: boolean,
): Promise<CurrentUser> {
  const action = active ? "reactivate" : "deactivate";
  const res = await fetch(`${apiBaseUrl()}/users/${userId}/${action}`, {
    method: "POST",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}
