"use client";

import { toast } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { MdTranslate } from "react-icons/md";

import { setLocaleAction } from "@/actions/locale.action";
import { type Locale, LOCALE_NAMES, LOCALES } from "@/i18n/config";
import { useI18n } from "@/i18n/provider";

/**
 * One-time language prompt shown on the first visit (before the visitor has a
 * `pforh_locale` cookie). The page is already rendered in the auto-detected
 * language; this toast lets the visitor switch to the other language with one
 * tap. Either choosing or dismissing persists a cookie, so it never reappears.
 *
 * Rendered by the root layout only when `localeChosen` is false.
 */
export function LocaleToast() {
  const { locale, dict } = useI18n();
  const router = useRouter();
  const shown = useRef(false);
  const chosen = useRef(false);

  useEffect(() => {
    if (shown.current) {
      return;
    }
    shown.current = true;

    const other = LOCALES.find((code) => code !== locale) as Locale;

    async function choose(next: Locale) {
      chosen.current = true;
      toast.clear();
      await setLocaleAction(next);
      router.refresh();
    }

    toast(dict.localePrompt.title, {
      description: dict.localePrompt.description,
      indicator: <MdTranslate />,
      timeout: 0,
      actionProps: {
        children: LOCALE_NAMES[other],
        onPress: () => void choose(other),
      },
      onClose: () => {
        // Persist the current (auto-detected) locale so we don't ask again,
        // unless the visitor already made an explicit choice above.
        if (!chosen.current) {
          void setLocaleAction(locale);
        }
      },
    });
  }, [dict, locale, router]);

  return null;
}
