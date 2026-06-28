"use server";

/** Server action that persists the visitor's language choice in a cookie. */

import { cookies } from "next/headers";

import { type Locale, LOCALE_COOKIE, normalizeLocale } from "@/i18n/config";

const ONE_YEAR_SECONDS = 60 * 60 * 24 * 365;

/** Persist the chosen locale. The client refreshes to re-render with it. */
export async function setLocaleAction(locale: Locale): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(LOCALE_COOKIE, normalizeLocale(locale), {
    httpOnly: false,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: ONE_YEAR_SECONDS,
  });
}
