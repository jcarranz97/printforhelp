/** Raw API calls for the auth domain (server-side only). */

import { ApiError, apiBaseUrl, toApiError } from "@/lib/api";

export type UserRole = "user" | "maintainer" | "admin";
export type Locale = "es" | "en";

export type CurrentUser = {
  id: string;
  username: string;
  role: UserRole;
  preferred_locale: Locale;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

/** Exchange credentials for a JWT. Throws {@link ApiError} on failure. */
export async function loginRequest(
  username: string,
  password: string,
): Promise<TokenResponse> {
  const res = await fetch(`${apiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ username, password }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as TokenResponse;
}

/** Fetch the authenticated user's profile, or null if the token is bad. */
export async function fetchMe(token: string): Promise<CurrentUser | null> {
  const res = await fetch(`${apiBaseUrl()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (res.status === 401 || res.status === 403) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CurrentUser;
}

export { ApiError };
