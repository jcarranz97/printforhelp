"use client";

import { Button } from "@heroui/react";
import { useState } from "react";

import { ShipmentForm } from "@/components/shipments/shipment-form";
import { useI18n } from "@/i18n/provider";

export type CenterChoice = { id: string; name: string; city: string };

/**
 * "New shipment" on the caller's own queue page.
 *
 * The centre-nested form knows which centre it belongs to; here the caller may
 * staff several, so they pick one first and the existing form takes over. With
 * exactly one centre the picker is skipped — there is nothing to choose.
 */
export function NewShipmentPanel({ centers }: { centers: CenterChoice[] }) {
  const { dict } = useI18n();
  const t = dict.myShipments;
  const [open, setOpen] = useState(false);
  const [centerId, setCenterId] = useState(centers[0]?.id ?? "");

  if (centers.length === 0) {
    return null;
  }

  if (!open) {
    return (
      <div className="mb-8">
        <Button onPress={() => setOpen(true)}>{t.newShipment}</Button>
      </div>
    );
  }

  return (
    <div className="mb-8 flex flex-col gap-3 rounded-2xl border border-[var(--card-border)] p-4">
      {centers.length > 1 && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t.chooseCenter}</span>
          <select
            className="rounded-md border border-default-300 bg-transparent px-3 py-2"
            value={centerId}
            onChange={(e) => setCenterId(e.target.value)}
          >
            {centers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.city}
              </option>
            ))}
          </select>
        </label>
      )}
      <ShipmentForm centerId={centerId} onDone={() => setOpen(false)} />
    </div>
  );
}
