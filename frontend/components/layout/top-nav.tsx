import { Button } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { getCurrentUser, logoutAction } from "@/actions/auth.action";
import { getServerI18n } from "@/i18n/server";

import { LocaleToggle } from "./locale-toggle";
import { NavTabs } from "./nav-tabs";
import { ThemeToggle } from "./theme-toggle";

/**
 * Global top navigation bar shown on every page: brand, the Tabs
 * navigation, the language selector, and the current auth state (login link
 * or username + logout). A single full-width bottom border acts as the
 * divider; the Tabs sit flush on it so the active indicator lands on the line.
 */
export async function TopNav() {
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-[var(--background)]">
      <div className="mx-auto flex h-14 max-w-5xl items-stretch justify-between gap-6 px-6">
        <div className="flex items-stretch gap-8">
          <Link href="/" className="flex items-center text-lg font-bold">
            PrintForHelp
          </Link>
          <NavTabs isAdmin={user?.role === "admin"} isLoggedIn={!!user} />
        </div>

        <div className="flex items-center gap-3 text-sm">
          <LocaleToggle />
          <ThemeToggle />
          {user ? (
            <>
              <span className="text-muted">
                {dict.header.greeting}{" "}
                <strong className="text-foreground">{user.username}</strong>
              </span>
              <form action={logoutAction}>
                <Button type="submit" size="sm" variant="secondary">
                  {dict.header.logout}
                </Button>
              </form>
            </>
          ) : (
            <Link href="/login" className={buttonVariants({ size: "sm" })}>
              {dict.header.login}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
