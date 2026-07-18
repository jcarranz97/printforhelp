"use server";

/** Server actions that record the visitor's language choice. */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { type Locale, LOCALE_COOKIE, normalizeLocale } from "@/i18n/config";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { setPreferredLocale } from "@/lib/users.api";

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/**
 * Persist the caller's locale to their account when signed in, so the email
 * worker (which has no cookie) sends notifications in the same language.
 * Best-effort: the on-screen language still works from the cookie if this
 * fails or the visitor is a guest.
 */
export async function persistLocaleAction(locale: Locale): Promise<void> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return;
  }
  try {
    await setPreferredLocale(token, normalizeLocale(locale));
    revalidatePath("/", "layout");
  } catch {
    // Non-fatal — the on-screen language is already set via the cookie.
  }
}

/** Persist the chosen locale (cookie for the UI + account for email). */
export async function setLocaleAction(locale: Locale): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(LOCALE_COOKIE, normalizeLocale(locale), {
    httpOnly: false,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: ONE_YEAR_SECONDS,
  });
  await persistLocaleAction(locale);
}
