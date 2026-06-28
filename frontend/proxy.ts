import { type NextRequest, NextResponse } from "next/server";

// Kept in sync with AUTH_COOKIE_NAME in lib/api.ts. Proxy runs on the
// edge runtime and must avoid importing server-only modules.
const AUTH_COOKIE_NAME = "pforh_token";

/**
 * Protect authenticated areas. Unauthenticated requests to `/admin/*`
 * are redirected to the login page with a `next` hint. Authorization
 * (role checks) is always re-enforced server-side (NFR-006); this guard
 * is only a UX redirect.
 */
export default function proxy(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("next", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/admin/:path*"],
};
