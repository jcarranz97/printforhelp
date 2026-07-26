"use client";

import {
  Alert,
  Button,
  Card,
  Chip,
  Input,
  Label,
  TextField,
} from "@heroui/react";
import Link from "next/link";
import { useState, useTransition } from "react";

import {
  addShipmentContentAction,
  removeShipmentContentAction,
} from "@/actions/shipments.action";
import { useI18n } from "@/i18n/provider";
import type { ShipmentContents } from "@/lib/shipments.api";

/**
 * The box manifest: what is inside, plus scan-to-pack for whoever is holding
 * it. Redacted lines render as a muted placeholder — the backend blanks
 * everything identifying for a viewer who may not see that package (FR-146),
 * so there is nothing here to hide client-side.
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

      {contents.entries.length === 0 ? (
        <p className="text-sm text-muted">{t.contentsEmpty}</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {contents.entries.map((entry) => (
            <li key={entry.id}>
              <Card>
                <Card.Content className="flex items-center justify-between gap-3 py-3">
                  {entry.kind === "box" ? (
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">
                        📦 {t.nestedBox} → {entry.child_destination ?? "—"}
                      </span>
                      <span className="text-sm text-muted">
                        {t.contentsSummary
                          .replace(
                            "{packages}",
                            String(entry.child_package_count ?? 0),
                          )
                          .replace("{units}", "—")}
                      </span>
                    </div>
                  ) : entry.redacted ? (
                    <span className="text-sm text-muted italic">
                      🔒 {t.contentsRedacted}
                    </span>
                  ) : (
                    <div className="flex flex-col gap-1">
                      <span className="font-medium">
                        {entry.quantity} × {entry.resource_name}
                      </span>
                      <span className="text-sm text-muted">
                        {entry.maker_username}
                        {entry.contribution_status && (
                          <>
                            {" · "}
                            <Chip size="sm" variant="soft">
                              {entry.contribution_status}
                            </Chip>
                          </>
                        )}
                      </span>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    {entry.tracking_token && (
                      <Link
                        href={`/track/${entry.tracking_token}`}
                        className="text-sm underline"
                      >
                        QR
                      </Link>
                    )}
                    {entry.child_tracking_token && (
                      <Link
                        href={`/track/${entry.child_tracking_token}`}
                        className="text-sm underline"
                      >
                        QR
                      </Link>
                    )}
                    {contents.can_manage_contents && (
                      <Button
                        size="sm"
                        variant="danger-soft"
                        isPending={isPending}
                        onPress={() => remove(entry.id)}
                      >
                        {t.removeContent}
                      </Button>
                    )}
                  </div>
                </Card.Content>
              </Card>
            </li>
          ))}
        </ul>
      )}

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
