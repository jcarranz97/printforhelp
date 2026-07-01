/**
 * Proxies the authenticated QR-bundle download from the backend, injecting
 * the caller's bearer token from the httpOnly cookie (the browser cannot).
 * Usage: `/tracking-bundle/{groupId}?format=pdf|png`.
 */

import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import { fetchQrBundle } from "@/lib/tracking.api";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ groupId: string }> },
): Promise<NextResponse> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { groupId } = await params;
  const format =
    request.nextUrl.searchParams.get("format") === "png" ? "png" : "pdf";

  const upstream = await fetchQrBundle(groupId, format, token);
  if (!upstream.ok || upstream.body === null) {
    return NextResponse.json(
      { error: "unavailable" },
      { status: upstream.status },
    );
  }
  const filename = `tracking-${groupId}.${format}`;
  return new NextResponse(upstream.body, {
    status: 200,
    headers: {
      "Content-Type": format === "png" ? "image/png" : "application/pdf",
      "Content-Disposition": `attachment; filename="${filename}"`,
    },
  });
}
