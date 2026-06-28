/** Server-only i18n helpers: resolve the request locale from the cookie, or
 * fall back to the browser's Accept-Language on the first visit. */

import { cookies, headers } from "next/headers";

import {
  type Locale,
  LOCALE_COOKIE,
  localeFromAcceptLanguage,
  normalizeLocale,
} from "./config";
import { type Dictionary, getDictionary } from "./dictionaries";

/**
 * Resolve the active locale. An explicit cookie choice wins; otherwise we
 * detect the visitor's preferred language from the Accept-Language header.
 */
async function resolveLocale(cookieValue: string | undefined): Promise<Locale> {
  if (cookieValue) {
    return normalizeLocale(cookieValue);
  }
  const headerStore = await headers();
  return localeFromAcceptLanguage(headerStore.get("accept-language"));
}

/** Resolve the active locale from the locale cookie (or browser default). */
export async function getLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  return resolveLocale(cookieStore.get(LOCALE_COOKIE)?.value);
}

/**
 * Resolve the active locale and its dictionary in one call. `localeChosen`
 * is `false` until the visitor has an explicit cookie — the UI uses it to
 * show the one-time language prompt.
 */
export async function getServerI18n(): Promise<{
  locale: Locale;
  dict: Dictionary;
  localeChosen: boolean;
}> {
  const cookieStore = await cookies();
  const cookieValue = cookieStore.get(LOCALE_COOKIE)?.value;
  const locale = await resolveLocale(cookieValue);
  return {
    locale,
    dict: getDictionary(locale),
    localeChosen: Boolean(cookieValue),
  };
}
