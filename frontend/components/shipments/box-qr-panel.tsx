"use client";

import { Button, Checkbox } from "@heroui/react";
import Link from "next/link";
import { useState } from "react";

import { useI18n } from "@/i18n/provider";
import { trackQrImageUrl } from "@/lib/tracking.api";

/**
 * The QR that gets taped to the physical box, plus the printable label.
 *
 * The image comes from the same unauthenticated `/qr/{token}` rewrite the
 * package QRs use. The label is authenticated (it embeds the manifest, which
 * is not public), so it goes through the bearer-injecting proxy route rather
 * than pointing the browser at the backend origin.
 */
export function BoxQrPanel({
  centerId,
  shipmentId,
  trackingToken,
}: {
  centerId: string;
  shipmentId: string;
  trackingToken: string;
}) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const [manifest, setManifest] = useState(true);
  const [copied, setCopied] = useState(false);

  const base = `/shipment-label/${shipmentId}?center=${centerId}`;

  return (
    <section className="mt-6 flex flex-col items-center gap-3">
      <h2 className="text-lg font-semibold">{t.boxQrTitle}</h2>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={trackQrImageUrl(trackingToken)}
        alt={t.boxQrTitle}
        className="h-40 w-40"
      />
      <p className="max-w-sm text-center text-sm text-muted">{t.boxQrHint}</p>

      {/* Nesting this box inside a bigger one is done by handing its code to
          the other box — so make the code reachable without printing a label
          or squinting at the QR. The scan page is the other route: it offers
          the caller's open boxes directly. */}
      <div className="flex flex-wrap items-center justify-center gap-3">
        <code className="rounded bg-default-100 px-2 py-1 font-mono text-xs">
          {trackingToken}
        </code>
        <Button
          size="sm"
          variant="tertiary"
          onPress={() => {
            void navigator.clipboard.writeText(trackingToken).then(() => {
              setCopied(true);
              setTimeout(() => setCopied(false), 2000);
            });
          }}
        >
          {copied ? t.codeCopied : t.copyCode}
        </Button>
        <Link href={`/track/${trackingToken}`} className="text-sm underline">
          {t.openScanPage}
        </Link>
      </div>
      <p className="max-w-sm text-center text-xs text-muted">{t.nestHint}</p>
      <Checkbox isSelected={manifest} onChange={setManifest}>
        {t.includeManifest}
      </Checkbox>
      <div className="flex flex-wrap justify-center gap-2">
        <Button
          size="sm"
          // A route handler on this origin, so `download` is honoured.
          onPress={() => {
            window.location.href = `${base}&format=pdf&manifest=${manifest ? 1 : 0}`;
          }}
        >
          {t.printLabelPdf}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onPress={() => {
            window.location.href = `${base}&format=png`;
          }}
        >
          {t.printLabelPng}
        </Button>
      </div>
    </section>
  );
}
