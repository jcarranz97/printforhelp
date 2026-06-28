"use client";

import { Accordion, Button, Card, Chip } from "@heroui/react";
import Link from "next/link";
import { useState } from "react";
import { FiChevronDown } from "react-icons/fi";

import { Markdown } from "@/components/comments/markdown";
import { useI18n } from "@/i18n/provider";
import type { Shipment, ShipmentStatus } from "@/lib/shipments.api";

import { ShipmentForm } from "./shipment-form";

type ShipmentsPanelProps = {
  centerId: string;
  shipments: Shipment[];
  canManage: boolean;
};

const STATUS_COLOR: Record<ShipmentStatus, "success" | "default" | "danger"> = {
  receiving: "success",
  closed: "default",
  cancelled: "danger",
};

function formatDate(iso: string, locale: string): string {
  const dt = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleDateString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/**
 * Always-visible list of a center's shipments (FR-130), grouped into open
 * (still `receiving`) and archived (`closed` / `cancelled`). Open shipments
 * are shown directly; archived ones live in an Accordion that is collapsed
 * by default. Each card links to the shipment detail page (where comments
 * and activity live) via a stretched link, so the Markdown description
 * renders without nesting anchors. Effective members get an inline "add
 * shipment" form here.
 */
export function ShipmentsPanel({
  centerId,
  shipments,
  canManage,
}: ShipmentsPanelProps) {
  const { dict, locale } = useI18n();
  const t = dict.shipments;
  const [showCreate, setShowCreate] = useState(false);

  const open = shipments.filter((s) => s.status === "receiving");
  const archived = shipments.filter((s) => s.status !== "receiving");

  function card(shipment: Shipment) {
    return (
      <li key={shipment.id}>
        <Card className="relative transition-shadow hover:shadow-md">
          <Card.Content className="flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap items-center gap-3">
                <Link
                  href={`/centers/${centerId}/shipments/${shipment.id}`}
                  className="font-semibold before:absolute before:inset-0 before:rounded-2xl focus-visible:outline-2 focus-visible:outline-offset-2"
                  aria-label={`${t.viewDetails} ${shipment.shipment_date}`}
                >
                  {formatDate(shipment.shipment_date, locale)}
                </Link>
                <Chip
                  color={STATUS_COLOR[shipment.status]}
                  variant="soft"
                  size="sm"
                >
                  {t.status[shipment.status]}
                </Chip>
              </div>
              <span className="text-sm text-muted">{t.viewDetails} →</span>
            </div>

            {shipment.destination && (
              <p className="text-sm">
                <span className="text-muted">{t.destination}: </span>
                {shipment.destination}
              </p>
            )}
            {shipment.description && <Markdown source={shipment.description} />}
          </Card.Content>
        </Card>
      </li>
    );
  }

  return (
    <section className="mt-8 flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold">{t.title}</h2>
          <p className="text-sm text-muted">{t.subtitle}</p>
        </div>
        {canManage && !showCreate && (
          <Button size="sm" onPress={() => setShowCreate(true)}>
            {t.addShipment}
          </Button>
        )}
      </div>

      {showCreate && (
        <ShipmentForm centerId={centerId} onDone={() => setShowCreate(false)} />
      )}

      {shipments.length === 0 && !showCreate ? (
        <p className="text-sm text-muted">{t.empty}</p>
      ) : (
        <>
          {open.length > 0 ? (
            <ul className="flex flex-col gap-4">{open.map(card)}</ul>
          ) : (
            archived.length > 0 && (
              <p className="text-sm text-muted">{t.noOpen}</p>
            )
          )}

          {archived.length > 0 && (
            <Accordion>
              <Accordion.Item id="archived">
                <Accordion.Heading>
                  <Accordion.Trigger>
                    {t.archivedHeading} ({archived.length})
                    <Accordion.Indicator>
                      <FiChevronDown />
                    </Accordion.Indicator>
                  </Accordion.Trigger>
                </Accordion.Heading>
                <Accordion.Panel>
                  <Accordion.Body>
                    <ul className="flex flex-col gap-4 pt-2">
                      {archived.map(card)}
                    </ul>
                  </Accordion.Body>
                </Accordion.Panel>
              </Accordion.Item>
            </Accordion>
          )}
        </>
      )}
    </section>
  );
}
