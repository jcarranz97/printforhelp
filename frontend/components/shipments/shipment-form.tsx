"use client";

import { Alert, Button, type Key, ListBox, Select } from "@heroui/react";
import { useEffect, useState, useTransition } from "react";

import {
  type DestinationOption,
  createShipmentAction,
  listDestinationCentersAction,
  updateShipmentAction,
} from "@/actions/shipments.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";
import type { Shipment, ShipmentStatus } from "@/lib/shipments.api";

const STATUSES: ShipmentStatus[] = ["receiving", "closed", "cancelled"];

type ShipmentFormProps = {
  centerId: string;
  /** When provided, the form edits this shipment instead of creating one. */
  shipment?: Shipment;
  onDone: () => void;
};

/** Inline create/edit form for a shipment (effective member, FR-129). */
export function ShipmentForm({
  centerId,
  shipment,
  onDone,
}: ShipmentFormProps) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const [date, setDate] = useState(shipment?.shipment_date ?? "");
  const [status, setStatus] = useState<ShipmentStatus>(
    shipment?.status ?? "receiving",
  );
  const [destination, setDestination] = useState(shipment?.destination ?? "");
  // "" means no relay hop — the destination is wherever the free-text says.
  const [destinationCenterId, setDestinationCenterId] = useState(
    shipment?.destination_collection_center_id ?? "",
  );
  const [centers, setCenters] = useState<DestinationOption[]>([]);

  useEffect(() => {
    let cancelled = false;
    listDestinationCentersAction(centerId).then((options) => {
      if (!cancelled) {
        setCenters(options);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [centerId]);
  const [description, setDescription] = useState(shipment?.description ?? "");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function submit() {
    if (!date) {
      setError(t.errorDateRequired);
      return;
    }
    setError(null);
    startTransition(async () => {
      const payload = {
        shipment_date: date,
        status,
        destination: destination.trim() || null,
        destination_collection_center_id: destinationCenterId || null,
        description: description.trim() || null,
      };
      const res = shipment
        ? await updateShipmentAction(centerId, shipment.id, payload)
        : await createShipmentAction(centerId, payload);
      if (res.error) {
        setError(res.error);
      } else {
        onDone();
      }
    });
  }

  const fieldClass =
    "rounded-lg border border-default-200 bg-default-50 px-3 py-2 text-sm";

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-default-200 bg-default-50/40 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t.date}</span>
          <input
            type="date"
            className={fieldClass}
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <div className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t.statusLabel}</span>
          <Select
            aria-label={t.statusLabel}
            value={status}
            onChange={(key: Key | null) =>
              setStatus((key as ShipmentStatus) ?? "receiving")
            }
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {STATUSES.map((s) => (
                  <ListBox.Item key={s} id={s} textValue={t.status[s]}>
                    {t.status[s]}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
      </div>

      <label className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t.destination}</span>
        <input
          type="text"
          className={fieldClass}
          placeholder={t.destinationPlaceholder}
          value={destination}
          onChange={(e) => setDestination(e.target.value)}
        />
      </label>

      {/* Setting this makes the shipment a relay leg: the receiving centre's
          staff can then sign for the box on arrival (FR-142/FR-144). Left
          empty for a final delivery, where only the free-text destination
          above applies. */}
      {centers.length > 0 && (
        <label className="flex flex-col gap-1 text-sm">
          <span className="font-medium">{t.destinationCenter}</span>
          <select
            className={fieldClass}
            value={destinationCenterId}
            onChange={(e) => setDestinationCenterId(e.target.value)}
          >
            <option value="">{t.destinationCenterNone}</option>
            {centers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} — {c.city}
              </option>
            ))}
          </select>
          <span className="text-xs text-muted">{t.destinationCenterHint}</span>
        </label>
      )}

      <div className="flex flex-col gap-1 text-sm">
        <span className="font-medium">{t.description}</span>
        <MarkdownEditor
          rows={3}
          ariaLabel={t.description}
          placeholder={t.descriptionPlaceholder}
          value={description}
          onChange={setDescription}
        />
      </div>

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <div className="flex gap-2">
        <Button size="sm" isPending={isPending} onPress={submit}>
          {shipment ? t.saveChanges : t.create}
        </Button>
        <Button size="sm" variant="ghost" onPress={onDone}>
          {t.cancel}
        </Button>
      </div>
    </div>
  );
}
