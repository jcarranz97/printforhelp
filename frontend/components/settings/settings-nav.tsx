import Link from "next/link";

import type { Dictionary } from "@/i18n/dictionaries/es";

type SettingsNavProps = {
  dict: Dictionary;
  /** Which item to render as the current page. */
  active: "profile" | "account" | "notifications";
};

const ITEM = "rounded-md px-3 py-2 text-sm transition-colors";
const ACTIVE = `${ITEM} border-l-2 border-accent bg-accent/10 pl-[10px] font-semibold text-accent`;
const LINK = `${ITEM} text-muted hover:bg-default-100 hover:text-foreground`;

/** Left-hand navigation for the settings pages (GitHub-style). */
export function SettingsNav({ dict, active }: SettingsNavProps) {
  const t = dict.settingsProfile;
  return (
    <nav className="flex flex-col gap-0.5">
      <Link
        href="/settings/profile"
        className={active === "profile" ? ACTIVE : LINK}
      >
        {t.navPublicProfile}
      </Link>
      <Link
        href="/settings/account"
        className={active === "account" ? ACTIVE : LINK}
      >
        {t.navAccount}
      </Link>
      <Link
        href="/settings/notifications"
        className={active === "notifications" ? ACTIVE : LINK}
      >
        {t.navNotifications}
      </Link>
      <span className="px-3 pt-2 text-xs text-muted/60">{t.navMoreSoon}</span>
    </nav>
  );
}
