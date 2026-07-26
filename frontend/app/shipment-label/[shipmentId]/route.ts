/**
 * Proxies the authenticated box-label download, injecting the caller's bearer
 * token from the httpOnly cookie (the browser cannot read it, and the backend
 * has no browser-reachable origin in production).
 * Usage: `/shipment-label/{shipmentId}?center={id}&format=pdf|png[&manifest=0]`.
 */

import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME, apiBaseUrl } from "@/lib/api";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ shipmentId: string }> },
): Promise<NextResponse> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const { shipmentId } = await params;
  const search = request.nextUrl.searchParams;
  // The backend route is center-nested, so the center id rides as a param.
  const centerId = search.get("center");
  if (!centerId) {
    return NextResponse.json({ error: "center required" }, { status: 400 });
  }
  const format = search.get("format") === "png" ? "png" : "pdf";
  const manifest = search.get("manifest") !== "0";

  const url =
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}` +
    `/label.${format}${format === "pdf" ? `?manifest=${manifest}` : ""}`;
  const upstream = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!upstream.ok || upstream.body === null) {
    return NextResponse.json(
      { error: "unavailable" },
      { status: upstream.status },
    );
  }
  const headers = new Headers({
    "Content-Type": format === "png" ? "image/png" : "application/pdf",
    "Content-Disposition": `attachment; filename="caja-${shipmentId}.${format}"`,
  });
  const length = upstream.headers.get("content-length");
  if (length) {
    headers.set("Content-Length", length);
  }
  return new NextResponse(upstream.body, { status: 200, headers });
}
