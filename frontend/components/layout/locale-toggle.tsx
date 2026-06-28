"use client";

import { Button, Dropdown, Header, Label, type Selection } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useTransition } from "react";
import { MdTranslate } from "react-icons/md";

import { setLocaleAction } from "@/actions/locale.action";
import { type Locale, LOCALE_NAMES, LOCALES } from "@/i18n/config";
import { useI18n } from "@/i18n/provider";

/**
 * Language selector rendered as a dropdown menu (HeroUI docs style): an
 * icon-only trigger opens a single-select menu with a checkmark on the active
 * language. Persists the choice via a cookie (server action) and refreshes so
 * server components re-render in the new language.
 */
export function LocaleToggle() {
  const { locale, dict } = useI18n();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  function onSelectionChange(keys: Selection) {
    if (keys === "all") {
      return;
    }
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
    <Dropdown>
      <Button
        isIconOnly
        size="sm"
        variant="tertiary"
        aria-label={dict.header.localeAriaLabel}
        isDisabled={isPending}
      >
        <MdTranslate />
      </Button>
      <Dropdown.Popover className="min-w-[200px]">
        <Dropdown.Menu
          selectionMode="single"
          disallowEmptySelection
          selectedKeys={new Set([locale])}
          onSelectionChange={onSelectionChange}
        >
          <Dropdown.Section>
            <Header>{dict.header.localeMenuHeading}</Header>
            {LOCALES.map((code) => (
              <Dropdown.Item
                key={code}
                id={code}
                textValue={LOCALE_NAMES[code]}
              >
                <Dropdown.ItemIndicator />
                <Label>{LOCALE_NAMES[code]}</Label>
              </Dropdown.Item>
            ))}
          </Dropdown.Section>
        </Dropdown.Menu>
      </Dropdown.Popover>
    </Dropdown>
  );
}
