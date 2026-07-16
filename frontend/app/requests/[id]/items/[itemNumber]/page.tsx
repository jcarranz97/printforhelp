import type { Metadata } from "next";
import { Card, Chip } from "@heroui/react";
import Link from "next/link";
import { cookies } from "next/headers";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { EntityFeed } from "@/components/comments/entity-feed";
import { WatchButton } from "@/components/notifications/watch-button";
import { ClaimForm } from "@/components/requests/claim-form";
import { CountryBadge } from "@/components/requests/country-badge";
import { ItemDescription } from "@/components/requests/item-description";
import {
  type ItemCenter,
  ItemPreferredCenters,
} from "@/components/requests/item-preferred-centers";
import { ItemCommitments } from "@/components/requests/item-commitments";
import { ItemNumberBadge } from "@/components/requests/item-number-badge";
import { ItemProgress } from "@/components/requests/item-progress";
import { ReopenItemButton } from "@/components/requests/reopen-item-button";
import { SourceLinkButton } from "@/components/resources/source-link-button";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
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
  // Without the token an unpublished campaign's item 404s — which is what a
  // leaked link should do for everyone except its author and maintainers.
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const item = await getRequestItem(id, itemNumber, token);
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
      listItemCommitments(id, itemNumber, token),
      listComments("request_item", item.id, token),
      listActivity("request_item", item.id, token),
      user
        ? fetchWatchStateAction("request_item", item.id)
        : Promise.resolve(false),
      getRequest(id, token),
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
  const isOpen = item.status === "open";

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
          {item.countries.length > 0 && (
            <CountryBadge
              codes={item.countries}
              onlyLabel={dict.requests.onlyCountry}
              locale={locale}
            />
          )}
          {item.status !== "open" && (
            <Chip variant="soft" size="sm" color="warning">
              {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
            </Chip>
          )}
          {canManage && item.status !== "open" && (
            <ReopenItemButton requestId={id} itemId={item.id} />
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

        {item.resource_source_url && (
          // Grab-the-file CTA so a maker can jump straight to MakerWorld /
          // the download without opening the part page.
          <div className="self-start">
            <SourceLinkButton url={item.resource_source_url} />
          </div>
        )}

        <ItemDescription
          requestId={id}
          itemId={item.id}
          description={item.description}
          canManage={canManage}
        />

        {item.resource_packaging_instructions && (
          <section className="flex flex-col gap-2">
            <h2 className="text-sm font-semibold text-muted">
              {t.packagingHeading}
            </h2>
            <CollapsibleMarkdown
              source={item.resource_packaging_instructions}
            />
          </section>
        )}

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
          <Card.Content className="flex flex-col gap-4 text-sm">
            <ItemProgress p={p} unit={item.unit} />
            <div
              className="flex flex-wrap gap-4 border-t pt-3 text-xs text-muted"
              style={{ borderColor: "var(--card-border)" }}
            >
              <span>
                {t.created}: {formatWhen(item.created_at, locale)}
              </span>
              <span>
                {t.lastActivity}: {formatWhen(item.last_activity_at, locale)}
              </span>
            </div>
          </Card.Content>
        </Card>

        {/* Commitments are welcome even when the goal is met or the item is
        closed — a maker who already has help ready can still send it. */}
        {user ? (
          <ClaimForm
            requestId={id}
            requestItemId={item.id}
            itemNumber={item.item_number}
            itemClosed={!isOpen}
            sourceUrl={item.resource_source_url ?? undefined}
            remaining={item.progress.remaining}
            committed={item.progress.committed_quantity}
            target={item.progress.target_quantity}
            contributorCount={item.progress.contributor_count}
          />
        ) : (
          <p className="text-sm text-muted">{dict.claim.loginToClaim}</p>
        )}
      </div>

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.commitmentsTitle}</h2>
          {commitments.length > 0 && (
            <p className="text-sm text-muted">{t.commitmentsSubtitle}</p>
          )}
        </div>
        <ItemCommitments
          commitments={commitments}
          currentUsername={user?.username ?? null}
        />
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
