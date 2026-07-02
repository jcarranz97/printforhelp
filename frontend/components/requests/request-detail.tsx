"use client";

import { Button, Card, Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { useState } from "react";

import {
  closeItemAction,
  closeRequestAction,
  removeItemAction,
} from "@/actions/requests.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { WatchButton } from "@/components/notifications/watch-button";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";
import { deriveItemState } from "@/lib/request-item-state";
import type { HelpState, RequestDetail, RequestItem } from "@/lib/requests.api";

const FILTER_KEYS = ["all", "needs_help", "committed", "completed"] as const;
type ItemFilter = (typeof FILTER_KEYS)[number];

import { AddItemForm } from "./add-item-form";
import { ClaimForm } from "./claim-form";
import { EditItemForm } from "./edit-item-form";
import { ItemNumberBadge } from "./item-number-badge";

/** Campaign detail: per-item progress, the claim flow, and item management. */
export function RequestDetailView({
  request,
  parts,
  partNames,
  isLoggedIn,
  canManage,
  initialWatching,
}: {
  request: RequestDetail;
  parts: Part[];
  partNames: Record<string, string>;
  isLoggedIn: boolean;
  canManage: boolean;
  initialWatching: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const statusT = dict.requests.status;
  const filterT = dict.requestItem.filters;
  const closeAction = closeRequestAction.bind(null, request.id);
  const isOpen = request.status === "open";
  // Default to "Needs help" so the parts still needing contributions surface
  // first; the community can switch to All/Committed/Completed.
  const [filter, setFilter] = useState<ItemFilter>("needs_help");
  const visibleItems =
    filter === "all"
      ? request.items
      : request.items.filter((item) => deriveItemState(item) === filter);

  return (
    <div className="flex flex-col gap-8">
      {request.image_url && (
        // External/stored cover image: a plain img avoids next/image host
        // allow-listing, matching the catalog cards.
        <img
          src={request.image_url}
          alt={request.title}
          className="max-h-72 w-full rounded-2xl object-cover"
        />
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{request.title}</h1>
            <Chip variant="soft" size="sm">
              {statusT[request.status]}
            </Chip>
          </div>
          {request.description && (
            <div className="mt-3 max-w-2xl">
              <CollapsibleMarkdown source={request.description} />
            </div>
          )}
          <p className="mt-3 text-sm text-muted">
            {t.deadline}: {request.deadline ?? t.noDeadline}
          </p>
        </div>
        {canManage && isOpen && (
          <div className="flex gap-2">
            <Link
              href={`/requests/${request.id}/edit`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.edit}
            </Link>
            <form
              action={async () => {
                await closeAction();
              }}
            >
              <Button type="submit" variant="secondary" size="sm">
                {t.close}
              </Button>
            </form>
          </div>
        )}
      </div>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{t.itemsHeading}</h2>
          {request.items.length > 1 && (
            <div className="flex flex-wrap gap-2">
              {FILTER_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setFilter(key)}
                  aria-pressed={filter === key}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                    filter === key
                      ? "bg-[color:var(--accent-strong)] text-white"
                      : "bg-default-100 text-foreground hover:bg-default-200"
                  }`}
                >
                  {filterT[key]}
                </button>
              ))}
            </div>
          )}
        </div>

        {visibleItems.length === 0 ? (
          <div
            className="flex flex-col items-start gap-3 rounded-2xl border border-dashed p-6 text-sm"
            style={{ borderColor: "var(--card-border)" }}
          >
            <p className="text-muted">{dict.requestItem.filterEmpty}</p>
            {isLoggedIn ? (
              <WatchButton
                entityType="request"
                entityId={request.id}
                initialWatching={initialWatching}
              />
            ) : (
              <Link
                href={`/login?next=/requests/${request.id}`}
                className="font-medium hover:underline"
                style={{ color: "var(--accent-strong)" }}
              >
                {dict.requestItem.filterEmptyLogin}
              </Link>
            )}
          </div>
        ) : (
          visibleItems.map((item) => (
            <ItemCard
              key={item.id}
              requestId={request.id}
              item={item}
              partName={partNames[item.resource_id] ?? item.resource_id}
              isLoggedIn={isLoggedIn}
              canManage={canManage && isOpen}
              canRemove={
                canManage &&
                isOpen &&
                item.status === "open" &&
                item.progress.committed_quantity === 0 &&
                request.items.length > 1
              }
            />
          ))
        )}

        {canManage && isOpen && (
          <Card>
            <Card.Header>
              <Card.Title>{t.addPartHeading}</Card.Title>
            </Card.Header>
            <Card.Content>
              <AddItemForm requestId={request.id} parts={parts} />
            </Card.Content>
          </Card>
        )}
      </section>
    </div>
  );
}

function ItemCard({
  requestId,
  item,
  partName,
  isLoggedIn,
  canManage,
  canRemove,
}: {
  requestId: string;
  item: RequestItem;
  partName: string;
  isLoggedIn: boolean;
  canManage: boolean;
  canRemove: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const claimT = dict.claim;
  const p = item.progress;
  const target = p.target_quantity;
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const closeItem = closeItemAction.bind(null, requestId, item.id);
  const removeItem = removeItemAction.bind(null, requestId, item.id);
  const itemHref = `/requests/${requestId}/items/${item.item_number}`;

  return (
    // The whole card links to the item page. A stretched overlay link covers
    // the card; the interactive controls below sit above it (`relative z-10`)
    // so the claim form and manage buttons keep working.
    <Card className="relative transition-shadow hover:shadow-md">
      <Link
        href={itemHref}
        aria-label={`${partName} #${item.item_number} — ${t.viewItem}`}
        className="absolute inset-0 z-0"
      />
      <Card.Header>
        <div className="flex items-center justify-between gap-3">
          <Card.Title>{partName}</Card.Title>
          <div className="relative z-10 flex items-center gap-2">
            {item.status !== "open" && (
              <Chip variant="soft" size="sm" color="warning">
                {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
              </Chip>
            )}
            {canManage && item.status === "open" && (
              <form
                action={async () => {
                  await closeItem();
                }}
              >
                <Button type="submit" variant="secondary" size="sm">
                  {t.closeItem}
                </Button>
              </form>
            )}
            {canRemove && (
              <form
                action={async () => {
                  await removeItem();
                }}
              >
                <Button type="submit" variant="secondary" size="sm">
                  {t.removeItem}
                </Button>
              </form>
            )}
          </div>
        </div>
        <div className="mt-1">
          <ItemNumberBadge number={item.item_number} />
        </div>
        <Card.Description>
          {t.target}: {target ?? t.openEnded}
        </Card.Description>
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

        {canManage && item.status === "open" && (
          <div
            className="relative z-10 mt-2 border-t pt-3"
            style={{ borderColor: "var(--card-border)" }}
          >
            <EditItemForm requestId={requestId} item={item} />
          </div>
        )}

        {item.status === "open" &&
          (isLoggedIn ? (
            <div className="relative z-10">
              <ClaimForm
                requestId={requestId}
                requestItemId={item.id}
                itemNumber={item.item_number}
              />
            </div>
          ) : (
            <p className="text-muted">{claimT.loginToClaim}</p>
          ))}
      </Card.Content>
    </Card>
  );
}
