/**
 * Proxies the authenticated QR-bundle download from the backend, injecting
 * the caller's bearer token from the httpOnly cookie (the browser cannot).
 * Usage: `/tracking-bundle/{groupId}?format=pdf|png[&seq_from=&seq_to=]`.
 */

import { cookies } from "next/headers";
import { type NextRequest, NextResponse } from "next/server";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import { fetchQrBundle, type QrBundleScope } from "@/lib/tracking.api";

/** Parse a positive integer query param, or undefined if absent/invalid. */
function positiveInt(raw: string | null): number | undefined {
  if (raw === null) {
    return undefined;
  }
  const value = Number(raw);
  return Number.isInteger(value) && value >= 1 ? value : undefined;
}

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
  // Reprint window for the per-unit QRs; the backend re-validates it.
  const seqFrom = positiveInt(search.get("seq_from"));
  const seqTo = positiveInt(search.get("seq_to"));

  const upstream = await fetchQrBundle(groupId, format, token, {
    scope,
    labels,
    message,
    messageText,
    seqFrom,
    seqTo,
  });
  if (!upstream.ok || upstream.body === null) {
    return NextResponse.json(
      { error: "unavailable" },
      { status: upstream.status },
    );
  }
  const filename = `tracking-${groupId}.${format}`;
  const headers = new Headers({
    "Content-Type": format === "png" ? "image/png" : "application/pdf",
    "Content-Disposition": `attachment; filename="${filename}"`,
  });
  // Re-streaming the body drops the upstream length, leaving a chunked
  // response the browser cannot show progress for — and a big bundle is tens
  // of MB. Carry it over so the download bar has a total to count against.
  const length = upstream.headers.get("content-length");
  if (length) {
    headers.set("Content-Length", length);
  }
  return new NextResponse(upstream.body, { status: 200, headers });
}
