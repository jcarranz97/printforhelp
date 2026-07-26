"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useState, useTransition } from "react";

import {
  addShipmentContentAction,
  removeShipmentContentAction,
} from "@/actions/shipments.action";
import { ShipmentContentsList } from "@/components/shipments/shipment-contents-list";
import { useI18n } from "@/i18n/provider";
import type { ShipmentContents } from "@/lib/shipments.api";

/**
 * The box console's manifest: what is inside, plus scan-to-pack for whoever is
 * holding it. The lines themselves are rendered by the shared
 * `ShipmentContentsList`, so a box reads identically here and on the public
 * scan page — this component adds only the editing around them.
 */
export function ShipmentContentsPanel({
  centerId,
  shipmentId,
  contents,
}: {
  centerId: string;
  shipmentId: string;
  contents: ShipmentContents;
}) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const [token, setToken] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function add() {
    const trimmed = token.trim();
    if (!trimmed) {
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await addShipmentContentAction(centerId, shipmentId, {
        tracking_token: trimmed,
      });
      if (res.error) {
        setError(res.error);
      } else {
        setToken("");
      }
    });
  }

  function remove(contentId: string) {
    setError(null);
    startTransition(async () => {
      const res = await removeShipmentContentAction(
        centerId,
        shipmentId,
        contentId,
      );
      if (res.error) {
        setError(res.error);
      }
    });
  }

  return (
    <section className="mt-8 flex flex-col gap-3">
      <div>
        <h2 className="text-lg font-semibold">{t.boxTitle}</h2>
        <p className="text-sm text-muted">
          {t.contentsSummary
            .replace("{packages}", String(contents.package_count))
            .replace("{units}", String(contents.units_total))}
          {contents.child_count > 0 &&
            ` · ${t.contentsNested.replace(
              "{count}",
              String(contents.child_count),
            )}`}
        </p>
        {contents.hidden_count > 0 && (
          <p className="text-sm text-muted">
            {t.contentsHidden.replace("{count}", String(contents.hidden_count))}
          </p>
        )}
      </div>

      <ShipmentContentsList
        entries={contents.entries}
        isPending={isPending}
        onRemove={contents.can_manage_contents ? remove : undefined}
      />

      {contents.can_manage_contents && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="flex items-end gap-2">
            <TextField
              className="flex-1"
              value={token}
              onChange={setToken}
              aria-label={t.addContent}
            >
              <Label>{t.addContent}</Label>
              <Input placeholder={t.addContentPlaceholder} />
            </TextField>
            <Button isPending={isPending} onPress={add}>
              {t.addContent}
            </Button>
          </div>
          <p className="text-xs text-muted">{t.addContentHint}</p>
        </div>
      )}

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </section>
  );
}
