"use client";

import { type Key, ToggleButton, ToggleButtonGroup } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { setLocaleAction } from "@/actions/locale.action";
import { type Locale, LOCALES } from "@/i18n/config";
import { useI18n } from "@/i18n/provider";

/**
 * ES/EN language selector (segmented control). Persists the choice via a
 * cookie (server action) and refreshes so server components re-render in the
 * new language.
 */
export function LocaleToggle() {
  const { locale, dict } = useI18n();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function onSelectionChange(keys: Set<Key>) {
    const next = [...keys][0] as Locale | undefined;
    if (!next || next === locale) {
      return;
    }
    startTransition(async () => {
      await setLocaleAction(next);
      router.refresh();
    });
  }

  return (
    <ToggleButtonGroup
      selectionMode="single"
      disallowEmptySelection
      size="sm"
      aria-label={dict.header.localeAriaLabel}
      selectedKeys={new Set([locale])}
      onSelectionChange={onSelectionChange}
      isDisabled={isPending}
    >
      {LOCALES.map((code, index) => (
        <ToggleButton key={code} id={code}>
          {index > 0 && <ToggleButtonGroup.Separator />}
          {code.toUpperCase()}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
