/** Raw API calls for the auth domain (server-side only). */

import { ApiError, apiBaseUrl, toApiError } from "@/lib/api";

export type UserRole = "user" | "maintainer" | "admin";
export type Locale = "es" | "en";

export type CurrentUser = {
  id: string;
  username: string;
  email: string | null;
  full_name: string | null;
  /** Public profile picture URL (a stored upload), or null (initials shown). */
  avatar_url: string | null;
  /** Short self-authored public blurb, or null. */
  bio: string | null;
  role: UserRole;
  preferred_locale: Locale;
  active: boolean;
  /** False while a Google sign-up still needs to pick their own username. */
  username_chosen: boolean;
  created_at: string;
  updated_at: string;
  /**
   * Generic per-user flags answered/granted so far (`{key: bool}`), present on
   * `/auth/me`. An absent key means "unknown" — e.g. `flags?.maker ===
   * undefined` before the user has answered the maker prompt. Optional because
   * the admin user list reuses this type and does not include flags.
   */
  flags?: Record<string, boolean>;
};

type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
};

/** Self-register a new account. Throws {@link ApiError} on failure. */
export async function registerRequest(
  fullName: string,
  username: string,
  email: string,
  password: string,
): Promise<TokenResponse> {
  const res = await fetch(`${apiBaseUrl()}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      full_name: fullName,
      username,
      email,
      password,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as TokenResponse;
}

/** Exchange a Google id_token for a JWT. Throws {@link ApiError} on failure. */
export async function googleLoginRequest(
  idToken: string,
): Promise<TokenResponse> {
  const res = await fetch(`${apiBaseUrl()}/auth/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as TokenResponse;
}

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

/**
 * Ask the backend to email a password-reset link. The response is always
 * the same whether or not the email is registered (no user enumeration),
 * so this only throws on an unexpected (non-2xx) failure.
 */
export async function forgotPasswordRequest(email: string): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/auth/forgot-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Redeem a reset token and set a new password. Throws on failure. */
export async function resetPasswordRequest(
  token: string,
  newPassword: string,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/auth/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token, new_password: newPassword }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Pick your own username (one-time, Google onboarding). Throws on failure. */
export async function chooseUsernameRequest(
  token: string,
  username: string,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/users/me/username`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ username }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
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
