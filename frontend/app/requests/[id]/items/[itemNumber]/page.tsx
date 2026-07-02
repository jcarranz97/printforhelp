import type { Metadata } from "next";
import { Card, Chip } from "@heroui/react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { EntityFeed } from "@/components/comments/entity-feed";
import { WatchButton } from "@/components/notifications/watch-button";
import { ClaimForm } from "@/components/requests/claim-form";
import { ItemDescription } from "@/components/requests/item-description";
import {
  type ItemCenter,
  ItemPreferredCenters,
} from "@/components/requests/item-preferred-centers";
import { ItemCommitments } from "@/components/requests/item-commitments";
import { ItemNumberBadge } from "@/components/requests/item-number-badge";
import { getServerI18n } from "@/i18n/server";
import { getCollectionCenter } from "@/lib/collection-centers.api";
import { listActivity, listComments } from "@/lib/feed.api";
import { markdownToExcerpt } from "@/lib/markdown-excerpt";
import { getOrganization } from "@/lib/organizations.api";
import {
  getRequest,
  getRequestItem,
  listItemCommitments,
  type RequestStatus,
} from "@/lib/requests.api";

const REQUEST_STATUS_COLOR: Record<
  RequestStatus,
  "success" | "default" | "warning"
> = {
  open: "success",
  fulfilled: "default",
  closed: "warning",
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string; itemNumber: string }>;
}): Promise<Metadata> {
  const { id, itemNumber } = await params;
  const item = await getRequestItem(id, itemNumber);
  const title = item
    ? `${item.resource_name} #${item.item_number}`
    : "PrintForHelp";
  return { title: `${title} · PrintForHelp` };
}

function formatWhen(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default async function RequestItemDetailPage({
  params,
}: {
  params: Promise<{ id: string; itemNumber: string }>;
}) {
  const { id, itemNumber } = await params;
  const item = await getRequestItem(id, itemNumber);
  if (!item) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict, locale } = await getServerI18n();
  const t = dict.requestItem;

  // Comments/activity/watch are keyed on the item's UUID (the number is only
  // for display + the URL), so use item.id for those reads.
  const [commitments, comments, activity, watching, request] =
    await Promise.all([
      listItemCommitments(id, itemNumber),
      listComments("request_item", item.id),
      listActivity("request_item", item.id),
      user
        ? fetchWatchStateAction("request_item", item.id)
        : Promise.resolve(false),
      getRequest(id),
    ]);

  // Show who requested it. Org-requested campaigns surface the org (or an
  // "unverified" badge when hidden); user-requested ones stay anonymous.
  const requesterOrg = request?.requester_organization_id
    ? await getOrganization(request.requester_organization_id)
    : null;
  const requesterLabel = requesterOrg
    ? `${t.requestedBy} ${requesterOrg.name}`
    : request?.requester_organization_id
      ? t.orgUnverified
      : t.communityRequest;

  const viewer = user ? { id: user.id, role: user.role } : null;

  // Resolve the request's preferred drop-off centers (candidates for this item)
  // to full details, preserving the request's order. Owners can narrow them to
  // just the ones this item is needed at.
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canManage =
    !!user && (user.id === request?.requester_user_id || isMaintainer);
  const candidateIds = request?.preferred_collection_center_ids ?? [];
  const candidates: ItemCenter[] = (
    await Promise.all(candidateIds.map((cid) => getCollectionCenter(cid)))
  )
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({
      id: c.id,
      name: c.name,
      city: c.city,
      country: c.country,
      location_url: c.location_url,
    }));

  const p = item.progress;
  const target = p.target_quantity;
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const isOpen = item.status === "open";
  // Suffix quantities with the item's unit (e.g. "5 litros"); empty for pieces.
  const unitSuffix = item.unit ? ` ${item.unit}` : "";

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between gap-4">
        <Link
          href={`/requests/${id}`}
          className="text-sm text-muted hover:underline"
        >
          {t.back}
        </Link>
        {user && (
          <WatchButton
            entityType="request_item"
            entityId={item.id}
            initialWatching={watching}
          />
        )}
      </div>

      <div className="mt-4 flex flex-col gap-6">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{item.resource_name}</h1>
          <ItemNumberBadge number={item.item_number} />
          {item.status !== "open" && (
            <Chip variant="soft" size="sm" color="warning">
              {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
            </Chip>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {request && (
            <section className="flex h-full flex-col gap-2">
              <h2 className="text-sm font-semibold text-muted">
                {t.whoHeading}
              </h2>
              <Link
                href={`/requests/${id}?from=item&fromItem=${item.item_number}`}
                className="block h-full rounded-2xl transition-shadow hover:shadow-md"
                aria-label={`${t.viewCampaign} ${request.title}`}
              >
                <Card className="flex h-full flex-col">
                  {request.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={request.image_url}
                      alt={request.title}
                      className="h-40 w-full rounded-t-2xl object-cover"
                    />
                  )}
                  <Card.Header>
                    <Card.Title>{request.title}</Card.Title>
                    {request.description && (
                      <Card.Description className="line-clamp-2">
                        {markdownToExcerpt(request.description)}
                      </Card.Description>
                    )}
                  </Card.Header>
                  <Card.Footer className="mt-auto flex flex-wrap items-center gap-2">
                    <Chip
                      color={REQUEST_STATUS_COLOR[request.status]}
                      variant="soft"
                      size="sm"
                    >
                      {dict.requests.status[request.status]}
                    </Chip>
                    <span className="text-xs text-muted">{requesterLabel}</span>
                  </Card.Footer>
                </Card>
              </Link>
            </section>
          )}

          <section className="flex h-full flex-col gap-2">
            <h2 className="text-sm font-semibold text-muted">
              {t.whatHeading}
            </h2>
            <Link
              href={`/parts/${item.resource_id}?from=item&fromReq=${id}&fromItem=${item.item_number}`}
              className="block h-full rounded-2xl transition-shadow hover:shadow-md"
              aria-label={`${t.viewPart} ${item.resource_name}`}
            >
              <Card className="flex h-full flex-col">
                {item.resource_image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.resource_image_url}
                    alt={item.resource_name}
                    className="h-40 w-full rounded-t-2xl object-cover"
                  />
                )}
                <Card.Header>
                  <Card.Title>{item.resource_name}</Card.Title>
                  {item.resource_description && (
                    <Card.Description className="line-clamp-2">
                      {markdownToExcerpt(item.resource_description)}
                    </Card.Description>
                  )}
                </Card.Header>
              </Card>
            </Link>
          </section>
        </div>

        <ItemDescription
          requestId={id}
          itemId={item.id}
          description={item.description}
          canManage={canManage}
        />

        {candidates.length > 0 && (
          <ItemPreferredCenters
            requestId={id}
            itemId={item.id}
            candidates={candidates}
            selectedIds={item.preferred_collection_center_ids}
            canManage={canManage}
          />
        )}

        <Card>
          <Card.Header>
            <Card.Title>
              {t.target}:{" "}
              {target != null ? `${target}${unitSuffix}` : t.openEnded}
            </Card.Title>
          </Card.Header>
          <Card.Content className="flex flex-col gap-3 text-sm">
            {target ? (
              <div
                className="flex h-2 w-full overflow-hidden rounded-full"
                style={{ background: "var(--card-border)" }}
              >
                <div
                  style={{
                    width: `${pct(p.at_center_quantity)}%`,
                    background: "var(--accent-strong)",
                  }}
                />
                <div
                  style={{
                    width: `${pct(p.claimed_quantity)}%`,
                    background: "var(--accent)",
                  }}
                />
              </div>
            ) : null}
            <div className="flex flex-wrap gap-4">
              <span>
                {t.progressClaimed}:{" "}
                <strong>
                  {p.claimed_quantity}
                  {unitSuffix}
                </strong>
              </span>
              <span>
                {t.progressAtCenter}:{" "}
                <strong>
                  {p.at_center_quantity}
                  {unitSuffix}
                </strong>
              </span>
              {p.remaining !== null && (
                <span>
                  {t.progressRemaining}:{" "}
                  <strong>
                    {p.remaining}
                    {unitSuffix}
                  </strong>
                </span>
              )}
            </div>
            <div className="flex flex-wrap gap-4 text-xs text-muted">
              <span>
                {t.created}: {formatWhen(item.created_at, locale)}
              </span>
              <span>
                {t.lastActivity}: {formatWhen(item.last_activity_at, locale)}
              </span>
            </div>
          </Card.Content>
        </Card>

        {isOpen &&
          (user ? (
            <ClaimForm
              requestId={id}
              requestItemId={item.id}
              itemNumber={item.item_number}
            />
          ) : (
            <p className="text-sm text-muted">{dict.claim.loginToClaim}</p>
          ))}
      </div>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.commitmentsTitle}</h2>
          {commitments.length > 0 && (
            <p className="text-sm text-muted">{t.commitmentsSubtitle}</p>
          )}
        </div>
        <ItemCommitments commitments={commitments} />
      </section>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/requests/${id}/items/${itemNumber}`}
          entityType="request_item"
          entityId={item.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
