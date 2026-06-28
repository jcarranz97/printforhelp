"use server";

/**
 * Server actions for authentication. This is the only place that reads
 * and writes the auth cookie (cookie access is server-only).
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { type CurrentUser, fetchMe, loginRequest } from "@/lib/auth.api";

const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

export type LoginState = { error: string | null };

/** Resolve the current user from the auth cookie, or null. */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  try {
    return await fetchMe(token);
  } catch {
    return null;
  }
}

/** Handle the login form submission (used with `useActionState`). */
export async function loginAction(
  _prevState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!username || !password) {
    return { error: "Ingresa tu usuario y contraseña." };
  }

  let token: string;
  try {
    const data = await loginRequest(username, password);
    token = data.access_token;
  } catch (error) {
    if (error instanceof ApiError && error.code === "INACTIVE_USER") {
      return { error: "Esta cuenta está inactiva." };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { error: "Usuario o contraseña incorrectos." };
    }
    return { error: "No se pudo iniciar sesión. Inténtalo de nuevo." };
  }

  const cookieStore = await cookies();
  cookieStore.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SEVEN_DAYS_SECONDS,
  });

  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect("/");
}

/** Clear the auth cookie and return to the landing page. */
export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_COOKIE_NAME);
  redirect("/");
}
