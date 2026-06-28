/** Server-only i18n helpers: resolve the request locale from the cookie. */

import { cookies } from "next/headers";

import { type Locale, LOCALE_COOKIE, normalizeLocale } from "./config";
import { type Dictionary, getDictionary } from "./dictionaries";

/** Resolve the active locale from the locale cookie (defaults to Spanish). */
export async function getLocale(): Promise<Locale> {
  const cookieStore = await cookies();
  return normalizeLocale(cookieStore.get(LOCALE_COOKIE)?.value);
}

/** Resolve the active locale and its dictionary in one call. */
export async function getServerI18n(): Promise<{
  locale: Locale;
  dict: Dictionary;
}> {
  const locale = await getLocale();
  return { locale, dict: getDictionary(locale) };
}
