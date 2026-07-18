"use client";

import { useEffect, useRef } from "react";

import { persistLocaleAction } from "@/actions/locale.action";
import type { Locale } from "@/i18n/config";

type LocaleSyncProps = {
  /** The language the UI is currently showing (cookie or auto-detected). */
  effectiveLocale: Locale;
  /** The language stored on the account (drives email). */
  accountLocale: Locale;
};

/**
 * Keeps the account's `preferred_locale` in step with the language the user is
 * actually reading the site in — including a first-visit language that was
 * auto-detected from `Accept-Language` and never explicitly chosen. Runs once
 * per mount and only when the two differ, so the email worker sends
 * notifications in the right language without any separate setting.
 */
export function LocaleSync({
  effectiveLocale,
  accountLocale,
}: LocaleSyncProps) {
  const synced = useRef(false);
  useEffect(() => {
    if (synced.current || effectiveLocale === accountLocale) {
      return;
    }
    synced.current = true;
    void persistLocaleAction(effectiveLocale);
  }, [effectiveLocale, accountLocale]);
  return null;
}
