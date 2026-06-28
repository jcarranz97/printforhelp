"use client";

import { Alert, Button, Card, Chip } from "@heroui/react";
import { useState, useTransition } from "react";

import { deleteShipmentAction } from "@/actions/shipments.action";
import { Markdown } from "@/components/comments/markdown";
import { EntityFeed, type FeedViewer } from "@/components/comments/entity-feed";
import { useI18n } from "@/i18n/provider";
import type { ActivityEntry, Comment } from "@/lib/feed.api";
import type { Shipment, ShipmentStatus } from "@/lib/shipments.api";

import { ShipmentForm } from "./shipment-form";

export type ShipmentFeed = { comments: Comment[]; activity: ActivityEntry[] };

type ShipmentsPanelProps = {
  centerId: string;
  shipments: Shipment[];
  feeds: Record<string, ShipmentFeed>;
  canManage: boolean;
  viewer: FeedViewer;
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

export function ShipmentsPanel({
  centerId,
  shipments,
  feeds,
  canManage,
  viewer,
}: ShipmentsPanelProps) {
  const { dict, locale } = useI18n();
  const t = dict.shipments;
  const [showCreate, setShowCreate] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [openFeedId, setOpenFeedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  function remove(shipmentId: string) {
    setError(null);
    startTransition(async () => {
      const res = await deleteShipmentAction(centerId, shipmentId);
      if (res.error) {
        setError(res.error);
      }
    });
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

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      {showCreate && (
        <ShipmentForm centerId={centerId} onDone={() => setShowCreate(false)} />
      )}

      {shipments.length === 0 && !showCreate ? (
        <p className="text-sm text-muted">{t.empty}</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {shipments.map((shipment) => {
            const feed = feeds[shipment.id] ?? { comments: [], activity: [] };
            const commentCount = feed.comments.length;
            const isEditing = editingId === shipment.id;
            const feedOpen = openFeedId === shipment.id;

            return (
              <li key={shipment.id}>
                <Card>
                  <Card.Content className="flex flex-col gap-3">
                    {isEditing ? (
                      <ShipmentForm
                        centerId={centerId}
                        shipment={shipment}
                        onDone={() => setEditingId(null)}
                      />
                    ) : (
                      <>
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <div className="flex flex-wrap items-center gap-3">
                            <span className="font-semibold">
                              {formatDate(shipment.shipment_date, locale)}
                            </span>
                            <Chip
                              color={STATUS_COLOR[shipment.status]}
                              variant="soft"
                              size="sm"
                            >
                              {t.status[shipment.status]}
                            </Chip>
                          </div>
                          {canManage && (
                            <div className="flex gap-3 text-xs">
                              <button
                                type="button"
                                className="text-muted hover:text-foreground"
                                onClick={() => setEditingId(shipment.id)}
                              >
                                {t.edit}
                              </button>
                              <button
                                type="button"
                                className="text-danger hover:underline"
                                disabled={isPending}
                                onClick={() => remove(shipment.id)}
                              >
                                {t.delete}
                              </button>
                            </div>
                          )}
                        </div>

                        {shipment.destination && (
                          <p className="text-sm">
                            <span className="text-muted">
                              {t.destination}:{" "}
                            </span>
                            {shipment.destination}
                          </p>
                        )}
                        {shipment.description && (
                          <Markdown source={shipment.description} />
                        )}

                        <button
                          type="button"
                          className="self-start text-xs text-muted hover:text-foreground"
                          onClick={() =>
                            setOpenFeedId(feedOpen ? null : shipment.id)
                          }
                        >
                          {feedOpen
                            ? t.hideComments
                            : `${t.comments} (${commentCount})`}
                        </button>

                        {feedOpen && (
                          <div className="border-t border-default-200 pt-3">
                            <EntityFeed
                              centerId={centerId}
                              entityType="shipment"
                              entityId={shipment.id}
                              comments={feed.comments}
                              activity={feed.activity}
                              viewer={viewer}
                            />
                          </div>
                        )}
                      </>
                    )}
                  </Card.Content>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
