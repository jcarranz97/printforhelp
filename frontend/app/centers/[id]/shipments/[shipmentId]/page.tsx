import { Card, Chip } from "@heroui/react";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { fetchReactionStateAction } from "@/actions/reactions.action";
import { Markdown } from "@/components/comments/markdown";
import { EntityFeed } from "@/components/comments/entity-feed";
import { LikeButton } from "@/components/reactions/like-button";
import { WatchButton } from "@/components/notifications/watch-button";
import { BoxQrPanel } from "@/components/shipments/box-qr-panel";
import { ShipmentContentsPanel } from "@/components/shipments/shipment-contents";
import { ShipmentLifecycle } from "@/components/shipments/shipment-lifecycle";
import { ShipmentManage } from "@/components/shipments/shipment-manage";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import {
  canManageCenter,
  getCollectionCenter,
} from "@/lib/collection-centers.api";
import { listActivity, listComments } from "@/lib/feed.api";
import {
  type ShipmentStatus,
  getShipment,
  listShipmentContents,
} from "@/lib/shipments.api";

const STATUS_COLOR: Record<
  ShipmentStatus,
  "success" | "default" | "danger" | "warning"
> = {
  receiving: "success",
  in_transit: "warning",
  arrived: "success",
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

export default async function ShipmentDetailPage({
  params,
}: {
  params: Promise<{ id: string; shipmentId: string }>;
}) {
  const { id, shipmentId } = await params;
  const user = await getCurrentUser();
  const token = user
    ? (await cookies()).get(AUTH_COOKIE_NAME)?.value
    : undefined;
  const { dict, locale } = await getServerI18n();
  const t = dict.shipments;

  const [center, shipment] = await Promise.all([
    getCollectionCenter(id, token),
    getShipment(id, shipmentId),
  ]);
  if (!center || !shipment) {
    notFound();
  }

  // When the next stop is another centre on the platform, name it — the
  // free-text destination alone gives the team nothing they can click.
  const destinationCenter = shipment.destination_collection_center_id
    ? await getCollectionCenter(
        shipment.destination_collection_center_id,
        token,
      )
    : null;

  const viewer = user ? { id: user.id, role: user.role } : null;
  const revalidate = `/centers/${id}/shipments/${shipmentId}`;
  const [canManage, contents, comments, activity, watching, reaction] =
    await Promise.all([
      canManageCenter(id, token),
      listShipmentContents(id, shipmentId, token),
      listComments("shipment", shipmentId),
      listActivity("shipment", shipmentId),
      user
        ? fetchWatchStateAction("shipment", shipmentId)
        : Promise.resolve(false),
      fetchReactionStateAction("shipment", shipmentId),
    ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link
        href={`/centers/${id}`}
        className="text-sm text-muted hover:text-foreground"
      >
        {t.detailBack} {center.name}
      </Link>

      <div className="mt-4 mb-8 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">
            {formatDate(shipment.shipment_date, locale)}
          </h1>
          <Chip color={STATUS_COLOR[shipment.status]} variant="soft" size="sm">
            {t.status[shipment.status]}
          </Chip>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <LikeButton
            entityType="shipment"
            entityId={shipmentId}
            initialCount={reaction.count}
            initialReacted={reaction.reacted}
            isAuthenticated={!!user}
          />
          {user && (
            <WatchButton
              entityType="shipment"
              entityId={shipmentId}
              initialWatching={watching}
            />
          )}
          {canManage && <ShipmentManage centerId={id} shipment={shipment} />}
        </div>
      </div>

      {contents.can_manage_contents && (
        <div className="mb-6">
          <ShipmentLifecycle centerId={id} shipment={shipment} />
        </div>
      )}

      <Card>
        <Card.Content className="flex flex-col gap-5">
          {/* Which centre is sending this. Obvious from the centre page, but
              the box console is also reached from /my-shipments and from a
              scanned QR, where it is not. */}
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              {t.origin}
            </span>
            <Link href={`/centers/${center.id}`} className="text-sm underline">
              {center.name}
            </Link>
            <span className="text-xs text-muted">
              {[center.city, center.state, center.country]
                .filter(Boolean)
                .join(", ")}
            </span>
          </div>

          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              {t.destination}
            </span>
            {destinationCenter ? (
              <>
                <Link
                  href={`/centers/${destinationCenter.id}`}
                  className="text-sm underline"
                >
                  {destinationCenter.name}
                </Link>
                <span className="text-xs text-muted">
                  {[
                    destinationCenter.city,
                    destinationCenter.state,
                    destinationCenter.country,
                  ]
                    .filter(Boolean)
                    .join(", ")}
                  {" · "}
                  {t.relayLeg}
                </span>
                {shipment.destination && (
                  <span className="text-xs text-muted">
                    {shipment.destination}
                  </span>
                )}
              </>
            ) : (
              <span className="text-sm">{shipment.destination ?? "-"}</span>
            )}
          </div>
          {shipment.description && (
            <div className="flex flex-col gap-1">
              <span className="text-xs font-medium uppercase tracking-wide text-muted">
                {t.description}
              </span>
              <Markdown source={shipment.description} />
            </div>
          )}
        </Card.Content>
      </Card>

      {contents.can_manage_contents && (
        <BoxQrPanel
          centerId={id}
          shipmentId={shipmentId}
          trackingToken={shipment.tracking_token}
        />
      )}

      <ShipmentContentsPanel
        centerId={id}
        shipmentId={shipmentId}
        contents={contents}
      />

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.commentsTitle}</h2>
          <p className="text-sm text-muted">{t.commentsSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={revalidate}
          entityType="shipment"
          entityId={shipmentId}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
