/** Locale configuration shared by server and client i18n helpers. */

export const LOCALES = ["es", "en"] as const;

export type Locale = (typeof LOCALES)[number];

/** Endonyms shown in the language picker (each language in its own name). */
export const LOCALE_NAMES: Record<Locale, string> = {
  es: "Español",
  en: "English",
};

/** Spanish-first per the v1 roadmap (NFR-015). */
export const DEFAULT_LOCALE: Locale = "es";

/** Cookie that persists the visitor's language choice. */
export const LOCALE_COOKIE = "pforh_locale";

/** Narrow an arbitrary string to a supported {@link Locale}, or the default. */
export function normalizeLocale(value: string | undefined): Locale {
  return LOCALES.includes(value as Locale) ? (value as Locale) : DEFAULT_LOCALE;
}

/**
 * Pick the best supported locale from an `Accept-Language` header value
 * (e.g. `"es-ES,es;q=0.9,en;q=0.8"`), honoring the quality weights. Used on
 * the very first visit, before the visitor has an explicit cookie choice.
 */
export function localeFromAcceptLanguage(
  header: string | null | undefined,
): Locale {
  if (!header) {
    return DEFAULT_LOCALE;
  }
  const ranked = header
    .split(",")
    .map((part) => {
      const [tag, q] = part.trim().split(";q=");
      return {
        code: tag.split("-")[0].toLowerCase(),
        quality: q ? Number.parseFloat(q) : 1,
      };
    })
    .sort((a, b) => b.quality - a.quality);

  const match = ranked.find(({ code }) => LOCALES.includes(code as Locale));
  return (match?.code as Locale) ?? DEFAULT_LOCALE;
}
