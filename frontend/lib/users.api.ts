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
