"use client";

import { Alert, Button } from "@heroui/react";
import { useState, useTransition } from "react";

import { shipmentLifecycleAction } from "@/actions/shipments.action";
import { useI18n } from "@/i18n/provider";
import type { Shipment } from "@/lib/shipments.api";

/**
 * The dock controls: dispatch a packed box, sign for an incoming one, or
 * re-run the bulk receipt. Which buttons appear follows the FR-141 status
 * map; the backend re-checks every transition (NFR-006).
 *
 * Marking a box arrived confirms receipt for everything inside it, so the
 * result counts are surfaced rather than swallowed — "37 confirmed, 3 already
 * received, 1 without a centre" is what tells the team whether to go looking
 * for something.
 */
export function ShipmentLifecycle({
  centerId,
  shipment,
}: {
  centerId: string;
  shipment: Shipment;
}) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function run(action: "dispatch" | "arrive" | "receive-contents") {
    setError(null);
    setSummary(null);
    startTransition(async () => {
      const res = await shipmentLifecycleAction(centerId, shipment.id, action);
      if (res.error) {
        setError(res.error);
        return;
      }
      if (res.arrival) {
        setSummary(
          t.arrivalResult
            .replace("{received}", String(res.arrival.received))
            .replace("{already}", String(res.arrival.skipped_already))
            .replace("{noCenter}", String(res.arrival.skipped_no_center)),
        );
      }
    });
  }

  const canDispatch = shipment.status === "receiving";
  const canArrive =
    shipment.status === "receiving" || shipment.status === "in_transit";
  const canReReceive = shipment.status === "arrived";

  if (!canDispatch && !canArrive && !canReReceive) {
    return null;
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <div className="flex flex-wrap gap-2">
        {canDispatch && (
          <Button
            size="sm"
            isPending={isPending}
            onPress={() => run("dispatch")}
          >
            {t.dispatch}
          </Button>
        )}
        {canArrive && (
          <Button
            size="sm"
            variant="secondary"
            isPending={isPending}
            onPress={() => run("arrive")}
          >
            {t.markArrived}
          </Button>
        )}
        {canReReceive && (
          <Button
            size="sm"
            variant="secondary"
            isPending={isPending}
            onPress={() => run("receive-contents")}
          >
            {t.receiveContents}
          </Button>
        )}
      </div>
      {summary && (
        <Alert status="success">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{summary}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
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
