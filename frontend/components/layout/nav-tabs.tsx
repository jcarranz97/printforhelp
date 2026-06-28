"use client";

import { Tabs } from "@heroui/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { useI18n } from "@/i18n/provider";

type NavTab = { id: string; href: string; label: string };

/** Map the current pathname to the matching tab key. */
function selectedKeyForPath(pathname: string): string {
  if (pathname.startsWith("/centers")) {
    return "centers";
  }
  if (pathname.startsWith("/admin")) {
    return "users";
  }
  if (pathname.startsWith("/about")) {
    return "about";
  }
  return "home";
}

/**
 * Top navigation built on HeroUI Tabs with the underlined (secondary)
 * indicator. Each tab is a Next.js link; the active tab is derived from
 * the current pathname so it stays in sync with client-side navigation.
 *
 * The "Users" tab is admin-only and is omitted for everyone else.
 */
export function NavTabs({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();
  const { dict } = useI18n();

  const homeTab: NavTab = { id: "home", href: "/", label: dict.nav.home };
  const centersTab: NavTab = {
    id: "centers",
    href: "/centers",
    label: dict.nav.centers,
  };
  const usersTab: NavTab = {
    id: "users",
    href: "/admin/users",
    label: dict.nav.users,
  };
  const aboutTab: NavTab = {
    id: "about",
    href: "/about",
    label: dict.nav.about,
  };

  const tabs = isAdmin
    ? [homeTab, centersTab, usersTab, aboutTab]
    : [homeTab, centersTab, aboutTab];
  const selectedKey = selectedKeyForPath(pathname);

  return (
    <Tabs
      variant="secondary"
      selectedKey={selectedKey}
      className="h-full justify-end"
    >
      <Tabs.ListContainer>
        <Tabs.List aria-label={dict.nav.ariaLabel} className="border-b-0">
          {tabs.map((tab) => (
            <Tabs.Tab
              key={tab.id}
              id={tab.id}
              href={tab.href}
              className="w-auto whitespace-nowrap"
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              render={(domProps: any) => <Link {...domProps} />}
            >
              {tab.label}
              <Tabs.Indicator />
            </Tabs.Tab>
          ))}
        </Tabs.List>
      </Tabs.ListContainer>
    </Tabs>
  );
}
