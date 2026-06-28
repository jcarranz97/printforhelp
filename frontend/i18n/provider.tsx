"use client";

/**
 * Client-side i18n context. The root layout (a server component) resolves
 * the locale + dictionary and passes them here so client components can read
 * translations via {@link useI18n} without re-reading the cookie.
 */

import { createContext, useContext } from "react";

import type { Locale } from "./config";
import type { Dictionary } from "./dictionaries";

type I18nValue = {
  locale: Locale;
  dict: Dictionary;
};

const I18nContext = createContext<I18nValue | null>(null);

export function I18nProvider({
  locale,
  dict,
  children,
}: I18nValue & { children: React.ReactNode }) {
  return (
    <I18nContext.Provider value={{ locale, dict }}>
      {children}
    </I18nContext.Provider>
  );
}

/** Read the active locale and dictionary inside a client component. */
export function useI18n(): I18nValue {
  const value = useContext(I18nContext);
  if (value === null) {
    throw new Error("useI18n must be used within an I18nProvider");
  }
  return value;
}
