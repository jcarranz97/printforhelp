"use client";

import { Alert, Button } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import { deleteShipmentAction } from "@/actions/shipments.action";
import { useI18n } from "@/i18n/provider";
import type { Shipment } from "@/lib/shipments.api";

import { ShipmentForm } from "./shipment-form";

/**
 * Edit / delete controls for a shipment on its detail page. Visible only
 * to effective members (the backend re-checks, NFR-006). Deleting returns
 * to the center page since the shipment no longer exists.
 */
export function ShipmentManage({
  centerId,
  shipment,
}: {
  centerId: string;
  shipment: Shipment;
}) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  if (editing) {
    return (
      <ShipmentForm
        centerId={centerId}
        shipment={shipment}
        onDone={() => setEditing(false)}
      />
    );
  }

  function remove() {
    setError(null);
    startTransition(async () => {
      const res = await deleteShipmentAction(centerId, shipment.id);
      if (res.error) {
        setError(res.error);
      } else {
        router.push(`/centers/${centerId}`);
      }
    });
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex gap-2">
        <Button size="sm" variant="secondary" onPress={() => setEditing(true)}>
          {t.edit}
        </Button>
        <Button
          size="sm"
          variant="danger-soft"
          isPending={isPending}
          onPress={remove}
        >
          {t.delete}
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
    </div>
  );
}
