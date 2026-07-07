/**
 * Proxies the authenticated QR-bundle download from the backend, injecting
 * the caller's bearer token from the httpOnly cookie (the browser cannot).
 * Usage: `/tracking-bundle/{groupId}?format=pdf|png`.
 */

import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import { fetchQrBundle, type QrBundleScope } from "@/lib/tracking.api";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ groupId: string }> },
): Promise<NextResponse> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { groupId } = await params;
  const search = request.nextUrl.searchParams;
  const format = search.get("format") === "png" ? "png" : "pdf";
  const scopeParam = search.get("scope");
  const scope: QrBundleScope =
    scopeParam === "group" || scopeParam === "individual" ? scopeParam : "both";
  const labels = search.get("labels") === "1";
  const message = search.get("message") === "1";
  const messageText = search.get("message_text") ?? undefined;

  const upstream = await fetchQrBundle(groupId, format, token, {
    scope,
    labels,
    message,
    messageText,
  });
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
