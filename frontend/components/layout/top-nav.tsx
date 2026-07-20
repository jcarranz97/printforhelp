import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchUnreadCountAction } from "@/actions/notifications.action";
import { getServerI18n } from "@/i18n/server";

import { LocaleToggle } from "./locale-toggle";
import { NavTabs } from "./nav-tabs";
import { NotificationsMenu } from "./notifications-menu";
import { ThemeToggle } from "./theme-toggle";
import { UserMenu } from "./user-menu";
import { profilePath } from "@/lib/profile-href";

/**
 * Global top navigation bar shown on every page: brand, the Tabs
 * navigation, the language selector, and the current auth state (login link
 * or username + logout). A single full-width bottom border acts as the
 * divider; the Tabs sit flush on it so the active indicator lands on the line.
 */
export async function TopNav() {
  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const unreadCount = user ? await fetchUnreadCountAction() : 0;

  return (
    <header className="border-b border-border bg-[var(--background)]">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:h-14 sm:flex-nowrap sm:items-stretch sm:justify-between sm:gap-6 sm:px-6 sm:py-0">
        <div className="order-1 flex h-11 flex-col justify-center sm:h-auto">
          <Link href="/" className="text-lg font-bold leading-tight">
            PrintForHelp
          </Link>
          {user?.flags?.maker === true && (
            <span className="text-xs text-muted">
              {dict.header.makerGreeting}{" "}
              <Link
                href={profilePath(user.username)}
                className="hover:underline"
              >
                {user.username}
              </Link>
            </span>
          )}
        </div>

        <div className="order-3 -mx-4 w-[calc(100%+2rem)] overflow-x-auto px-4 sm:order-2 sm:mx-0 sm:w-auto sm:overflow-visible sm:px-0">
          <NavTabs
            isAdmin={user?.role === "admin"}
            isMaintainer={user?.role === "maintainer" || user?.role === "admin"}
            isLoggedIn={!!user}
          />
        </div>

        <div className="order-2 ml-auto flex h-11 shrink-0 items-center gap-2 text-sm sm:order-3 sm:h-auto sm:gap-3">
          <LocaleToggle />
          <div className="hidden sm:block">
            <ThemeToggle />
          </div>
          {user ? (
            <>
              <NotificationsMenu initialUnread={unreadCount} />
              <UserMenu
                username={user.username}
                fullName={user.full_name}
                avatarUrl={user.avatar_url}
                crop={{
                  x: user.avatar_crop_x,
                  y: user.avatar_crop_y,
                  w: user.avatar_crop_w,
                  h: user.avatar_crop_h,
                }}
              />
            </>
          ) : (
            <Link
              href="/login"
              className={`${buttonVariants({ size: "sm" })} min-h-11 sm:min-h-9`}
            >
              {dict.header.login}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
