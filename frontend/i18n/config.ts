/** Locale configuration shared by server and client i18n helpers. */

export const LOCALES = ["es", "en"] as const;

export type Locale = (typeof LOCALES)[number];

/** Spanish-first per the v1 roadmap (NFR-015). */
export const DEFAULT_LOCALE: Locale = "es";

/** Cookie that persists the visitor's language choice. */
export const LOCALE_COOKIE = "pforh_locale";

/** Narrow an arbitrary string to a supported {@link Locale}, or the default. */
export function normalizeLocale(value: string | undefined): Locale {
  return LOCALES.includes(value as Locale) ? (value as Locale) : DEFAULT_LOCALE;
}
