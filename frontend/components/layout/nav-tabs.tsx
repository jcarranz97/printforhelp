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
  if (pathname.startsWith("/requests")) {
    return "requests";
  }
  if (pathname.startsWith("/parts")) {
    return "parts";
  }
  if (pathname.startsWith("/my-contributions")) {
    return "myContributions";
  }
  if (pathname.startsWith("/admin/notices")) {
    return "notices";
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
 * The "My prints" tab is shown only to logged-in users; the "Users" tab
 * is admin-only and the "Notices" tab is shown to maintainers and admins.
 * The rest are omitted for everyone else.
 */
export function NavTabs({
  isAdmin,
  isMaintainer,
  isLoggedIn,
}: {
  isAdmin: boolean;
  isMaintainer: boolean;
  isLoggedIn: boolean;
}) {
  const pathname = usePathname();
  const { dict } = useI18n();

  const homeTab: NavTab = { id: "home", href: "/", label: dict.nav.home };
  const centersTab: NavTab = {
    id: "centers",
    href: "/centers",
    label: dict.nav.centers,
  };
  const requestsTab: NavTab = {
    id: "requests",
    href: "/requests",
    label: dict.nav.requests,
  };
  const partsTab: NavTab = {
    id: "parts",
    href: "/parts",
    label: dict.nav.parts,
  };
  const myContributionsTab: NavTab = {
    id: "myContributions",
    href: "/my-contributions",
    label: dict.nav.myContributions,
  };
  const usersTab: NavTab = {
    id: "users",
    href: "/admin/users",
    label: dict.nav.users,
  };
  const noticesTab: NavTab = {
    id: "notices",
    href: "/admin/notices",
    label: dict.nav.notices,
  };
  const reviewTab: NavTab = {
    id: "review",
    href: "/admin/requests",
    label: dict.nav.review,
  };
  const aboutTab: NavTab = {
    id: "about",
    href: "/about",
    label: dict.nav.about,
  };

  const tabs: NavTab[] = [homeTab, centersTab, requestsTab, partsTab];
  if (isLoggedIn) {
    tabs.push(myContributionsTab);
  }
  if (isMaintainer) {
    tabs.push(reviewTab);
    tabs.push(noticesTab);
  }
  if (isAdmin) {
    tabs.push(usersTab);
  }
  tabs.push(aboutTab);
  const selectedKey = selectedKeyForPath(pathname);

  return (
    <Tabs
      variant="secondary"
      selectedKey={selectedKey}
      className="h-11 justify-start sm:h-full sm:justify-end"
    >
      <Tabs.ListContainer>
        <Tabs.List
          aria-label={dict.nav.ariaLabel}
          className="min-h-11 border-b-0 sm:min-h-0"
        >
          {tabs.map((tab) => (
            <Tabs.Tab
              key={tab.id}
              id={tab.id}
              href={tab.href}
              className="min-h-11 w-auto whitespace-nowrap sm:min-h-0"
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
