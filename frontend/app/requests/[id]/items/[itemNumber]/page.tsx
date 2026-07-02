import type { Metadata } from "next";
import { Card, Chip } from "@heroui/react";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { EntityFeed } from "@/components/comments/entity-feed";
import { WatchButton } from "@/components/notifications/watch-button";
import { ClaimForm } from "@/components/requests/claim-form";
import { ItemCommitments } from "@/components/requests/item-commitments";
import { ItemNumberBadge } from "@/components/requests/item-number-badge";
import { getServerI18n } from "@/i18n/server";
import { listActivity, listComments } from "@/lib/feed.api";
import { getRequestItem, listItemCommitments } from "@/lib/requests.api";

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
  const [commitments, comments, activity, watching] = await Promise.all([
    listItemCommitments(id, itemNumber),
    listComments("request_item", item.id),
    listActivity("request_item", item.id),
    user
      ? fetchWatchStateAction("request_item", item.id)
      : Promise.resolve(false),
  ]);

  const viewer = user ? { id: user.id, role: user.role } : null;

  const p = item.progress;
  const target = p.target_quantity;
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
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
        {item.resource_image_url && (
          // External/stored image: a plain img avoids next/image host
          // allow-listing, matching the catalog cards.
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.resource_image_url}
            alt={item.resource_name}
            className="max-h-64 w-full rounded-2xl object-cover"
          />
        )}

        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm text-muted">{item.request_title}</p>
            <div className="mt-1 flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-bold">{item.resource_name}</h1>
              <ItemNumberBadge number={item.item_number} />
              {item.status !== "open" && (
                <Chip variant="soft" size="sm" color="warning">
                  {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
                </Chip>
              )}
            </div>
            {item.resource_source_url && (
              <a
                href={item.resource_source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block text-sm font-medium underline"
                style={{ color: "var(--accent-strong)" }}
              >
                {t.viewSource}
              </a>
            )}
          </div>
        </div>

        {item.description && (
          <div className="max-w-2xl">
            <CollapsibleMarkdown source={item.description} />
          </div>
        )}

        <Card>
          <Card.Header>
            <Card.Title>
              {t.target}: {target ?? t.openEnded}
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
                {t.progressClaimed}: <strong>{p.claimed_quantity}</strong>
              </span>
              <span>
                {t.progressAtCenter}: <strong>{p.at_center_quantity}</strong>
              </span>
              {p.remaining !== null && (
                <span>
                  {t.progressRemaining}: <strong>{p.remaining}</strong>
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
