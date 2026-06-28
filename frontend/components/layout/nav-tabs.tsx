"use client";

import { Tabs } from "@heroui/react";
import Link from "next/link";
import { usePathname } from "next/navigation";

type NavTab = { id: string; href: string; label: string };

const HOME_TAB: NavTab = { id: "home", href: "/", label: "Home" };
const ABOUT_TAB: NavTab = { id: "about", href: "/about", label: "About Us" };
const USERS_TAB: NavTab = { id: "users", href: "/admin/users", label: "Users" };

/** Map the current pathname to the matching tab key. */
function selectedKeyForPath(pathname: string): string {
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
 * The list is bottom-aligned (`h-full justify-end`) so its underline
 * lines up with the full-width header border, forming a single divider
 * with the accent indicator sitting on it.
 *
 * The "Users" tab is admin-only and is omitted for everyone else.
 */
export function NavTabs({ isAdmin }: { isAdmin: boolean }) {
  const pathname = usePathname();
  const tabs = isAdmin
    ? [HOME_TAB, USERS_TAB, ABOUT_TAB]
    : [HOME_TAB, ABOUT_TAB];
  const selectedKey = selectedKeyForPath(pathname);

  return (
    <Tabs
      variant="secondary"
      selectedKey={selectedKey}
      className="h-full justify-end"
    >
      <Tabs.ListContainer>
        <Tabs.List aria-label="Navegación principal" className="border-b-0">
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
