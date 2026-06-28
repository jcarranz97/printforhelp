import { Button } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import { getCurrentUser, logoutAction } from "@/actions/auth.action";

import { NavTabs } from "./nav-tabs";

/**
 * Global top navigation bar shown on every page: brand, the Tabs
 * navigation, and the current auth state (login link or username +
 * logout). A single full-width bottom border acts as the divider; the
 * Tabs sit flush on it so the active indicator lands on the line.
 */
export async function TopNav() {
  const user = await getCurrentUser();

  return (
    <header className="border-b border-border">
      <div className="mx-auto flex h-14 max-w-5xl items-stretch justify-between gap-6 px-6">
        <div className="flex items-stretch gap-8">
          <Link href="/" className="flex items-center text-lg font-bold">
            PrintForHelp
          </Link>
          <NavTabs isAdmin={user?.role === "admin"} />
        </div>

        <div className="flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="text-muted">
                Hola,{" "}
                <strong className="text-foreground">{user.username}</strong>
              </span>
              <form action={logoutAction}>
                <Button type="submit" size="sm" variant="secondary">
                  Cerrar sesión
                </Button>
              </form>
            </>
          ) : (
            <Link href="/login" className={buttonVariants({ size: "sm" })}>
              Iniciar sesión
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
