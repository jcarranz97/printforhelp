"use client";

import { Alert, Button, Card } from "@heroui/react";
import Link from "next/link";
import { useState, useTransition } from "react";

import { addShipmentContentAction } from "@/actions/shipments.action";
import { useI18n } from "@/i18n/provider";
import type { PackingContext } from "@/lib/tracking.api";

/**
 * "File this into a box" on the public scan page.
 *
 * The packing-table workflow the box QRs exist for: a centre member scans
 * whatever is in their hand — a unit, a whole contribution, or another box —
 * and drops it into a shipment without navigating anywhere. Scanning a single
 * unit files its entire contribution, because contributions are what get
 * packed.
 *
 * Rendered only when the backend supplied a `packing` block, which it does
 * solely for someone who staffs a centre. Makers and passers-by scanning the
 * same QR see nothing.
 */
export function PackIntoBox({
  trackingToken,
  packing,
}: {
  trackingToken: string;
  packing: PackingContext;
}) {
  const { dict } = useI18n();
  const t = dict.tracking;
  const [selected, setSelected] = useState(
    packing.options[0]?.shipment_id ?? "",
  );
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // One thing rides in one box, so a packed item offers no picker — just where
  // it is, and a way to get there.
  if (packing.current_shipment_id) {
    return (
      <Card className="mt-6">
        <Card.Content className="flex flex-wrap items-center justify-between gap-3">
          <span className="text-sm">
            {t.packedInBox}{" "}
            <span className="font-medium">
              {packing.current_shipment_label}
            </span>
          </span>
          {packing.current_shipment_token && (
            <Link
              href={`/track/${packing.current_shipment_token}`}
              className="text-sm underline"
            >
              {t.openBoxLink}
            </Link>
          )}
        </Card.Content>
      </Card>
    );
  }

  if (packing.options.length === 0) {
    return null;
  }

  function pack() {
    const option = packing.options.find((o) => o.shipment_id === selected);
    if (!option) {
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await addShipmentContentAction(
        option.collection_center_id,
        option.shipment_id,
        { tracking_token: trackingToken },
      );
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <Card className="mt-6">
      <Card.Header>
        <Card.Title className="text-base">{t.packTitle}</Card.Title>
        <Card.Description>{t.packSubtitle}</Card.Description>
      </Card.Header>
      <Card.Content className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
            <span className="font-medium">{t.packChooseBox}</span>
            <select
              className="rounded-md border border-[var(--card-border)] bg-transparent px-3 py-2"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {packing.options.map((option) => (
                <option key={option.shipment_id} value={option.shipment_id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <Button isPending={isPending} onPress={pack}>
            {t.packAction}
          </Button>
        </div>
        {error && (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </Card.Content>
    </Card>
  );
}
