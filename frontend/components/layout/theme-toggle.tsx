"use client";

import { type Key, ToggleButton, ToggleButtonGroup } from "@heroui/react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { FiMonitor, FiMoon, FiSun } from "react-icons/fi";

import { useI18n } from "@/i18n/provider";

/**
 * Light / dark / system theme switcher (segmented icon control), mirroring the
 * HeroUI docs header. Persists via next-themes (`data-theme` on <html>). The
 * group is disabled until mounted to avoid a hydration mismatch, since the
 * resolved theme is only known on the client.
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { dict } = useI18n();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  const current = mounted ? (theme ?? "system") : "system";

  function onSelectionChange(keys: Set<Key>) {
    const next = [...keys][0] as string | undefined;
    if (next) {
      setTheme(next);
    }
  }

  return (
    <ToggleButtonGroup
      isDetached
      selectionMode="single"
      disallowEmptySelection
      size="sm"
      aria-label={dict.header.themeAriaLabel}
      selectedKeys={new Set([current])}
      onSelectionChange={onSelectionChange}
      isDisabled={!mounted}
      className="gap-1 rounded-full p-1 bg-[color-mix(in_srgb,var(--foreground)_8%,transparent)]"
    >
      <ToggleButton
        isIconOnly
        id="light"
        aria-label={dict.header.themeLight}
        className="rounded-full"
      >
        <FiSun />
      </ToggleButton>
      <ToggleButton
        isIconOnly
        id="dark"
        aria-label={dict.header.themeDark}
        className="rounded-full"
      >
        <FiMoon />
      </ToggleButton>
      <ToggleButton
        isIconOnly
        id="system"
        aria-label={dict.header.themeSystem}
        className="rounded-full"
      >
        <FiMonitor />
      </ToggleButton>
    </ToggleButtonGroup>
  );
}
