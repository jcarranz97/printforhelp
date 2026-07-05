"use client";

import { Button, Card, Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { useEffect, useState } from "react";

import {
  closeItemAction,
  closeRequestAction,
  removeItemAction,
  reopenItemAction,
  reopenRequestAction,
} from "@/actions/requests.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { WatchButton } from "@/components/notifications/watch-button";
import { BANNER_ASPECT_CSS } from "@/components/requests/request-image-field";
import { useI18n } from "@/i18n/provider";
import type { ResourceOption } from "@/lib/resource-options";
import { deriveItemState } from "@/lib/request-item-state";
import type { HelpState, RequestDetail, RequestItem } from "@/lib/requests.api";

const FILTER_KEYS = ["all", "needs_help", "completed"] as const;
type ItemFilter = (typeof FILTER_KEYS)[number];

import { AddItemForm } from "./add-item-form";
import { ClaimForm } from "./claim-form";
import { CountryBadge } from "./country-badge";
import { EditItemForm } from "./edit-item-form";
import { ItemNumberBadge } from "./item-number-badge";

/** Format an item's creation timestamp for its card. */
function formatItemDate(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Campaign detail: per-item progress, the claim flow, and item management. */
export function RequestDetailView({
  request,
  resources,
  resourceNames,
  isLoggedIn,
  canManage,
  initialWatching,
}: {
  request: RequestDetail;
  resources: ResourceOption[];
  resourceNames: Record<string, string>;
  isLoggedIn: boolean;
  canManage: boolean;
  initialWatching: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const statusT = dict.requests.status;
  const filterT = dict.requestItem.filters;
  const closeAction = closeRequestAction.bind(null, request.id);
  const reopenAction = reopenRequestAction.bind(null, request.id);
  const isOpen = request.status === "open";
  // Default to "Needs help" so the parts still needing contributions surface
  // first; the community can switch to All/Committed/Completed.
  const [filter, setFilter] = useState<ItemFilter>("needs_help");
  const [highlightId, setHighlightId] = useState<string | null>(null);

  // Deep-link support: a notification for a newly added item links here with
  // `#item-<id>`. Switch to "All" (so the item is visible regardless of its
  // help-state bucket), scroll to it, and flash a highlight. Runs on mount and
  // on later hash changes (same-page navigations from the notifications menu).
  useEffect(() => {
    function applyHash() {
      const hash = window.location.hash;
      if (!hash.startsWith("#item-")) {
        return;
      }
      const id = hash.slice("#item-".length);
      setFilter("all");
      setHighlightId(id);
      requestAnimationFrame(() => {
        document
          .getElementById(`item-${id}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

  // Clear the highlight a few seconds after it is applied.
  useEffect(() => {
    if (highlightId === null) {
      return;
    }
    const timer = setTimeout(() => setHighlightId(null), 3000);
    return () => clearTimeout(timer);
  }, [highlightId]);

  // Newest item first, so a just-added item appears at the top of the list.
  // created_at is an ISO string, so a lexicographic compare is chronological.
  const sortedItems = [...request.items].sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  );
  // "Needs help" also surfaces still-open items that have enough commitments
  // (committed state) — they are not completed, so they belong with the parts
  // the community can still jump in on.
  const visibleItems =
    filter === "all"
      ? sortedItems
      : sortedItems.filter((item) => {
          const state = deriveItemState(item);
          return filter === "needs_help"
            ? state === "needs_help" || state === "committed"
            : state === filter;
        });

  // Bucket used to offer a filter shortcut in the empty state so late helpers
  // can jump straight to completed items.
  const hasCompleted = sortedItems.some(
    (item) => deriveItemState(item) === "completed",
  );

  return (
    <div className="flex flex-col gap-8">
      {request.image_url && (
        // External/stored cover image: a plain img avoids next/image host
        // allow-listing, matching the catalog cards.
        <img
          src={request.image_url}
          alt={request.title}
          className="w-full rounded-2xl object-cover"
          style={{
            aspectRatio: BANNER_ASPECT_CSS,
            objectPosition: `${request.image_focus_x}% ${request.image_focus_y}%`,
          }}
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
          {request.beneficiary && (
            <p className="mt-3 max-w-2xl text-sm">
              <span className="font-medium">{t.beneficiaryHeading}:</span>{" "}
              {request.beneficiary}
            </p>
          )}
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
        {canManage && !isOpen && (
          // Undo an accidental close: reopen the campaign and its items.
          <form
            action={async () => {
              await reopenAction();
            }}
          >
            <Button type="submit" size="sm">
              {t.reopen}
            </Button>
          </form>
        )}
      </div>

      <section className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold">{t.itemsHeading}</h2>
          {request.items.length > 0 && (
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

        {/* Subtle reminder while items are listed; when the filter is empty the
        same message is shown highlighted in the empty-state box below. */}
        {visibleItems.length > 0 && (
          <p className="text-xs text-muted">{t.lateHelpNote}</p>
        )}

        {/* The "add item" form sits at the top so a requester can always add a
        needed part/supply without scrolling past the whole list. */}
        {canManage && isOpen && (
          <Card>
            <Card.Header>
              <Card.Title>{t.addPartHeading}</Card.Title>
            </Card.Header>
            <Card.Content>
              <AddItemForm requestId={request.id} resources={resources} />
            </Card.Content>
          </Card>
        )}

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
            {/* Highlighted callout so late helpers notice they can still
            contribute, with a quick shortcut to the completed items. */}
            <div
              className="flex flex-col gap-2 rounded-lg border px-3 py-3 text-sm font-medium"
              style={{
                borderColor: "var(--accent-strong)",
                color: "var(--accent-strong)",
                background:
                  "color-mix(in srgb, var(--accent-strong) 8%, transparent)",
              }}
            >
              <p>{t.lateHelpNote}</p>
              {hasCompleted && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs">{t.jumpTo}</span>
                  {hasCompleted && (
                    <button
                      type="button"
                      onClick={() => setFilter("completed")}
                      className="inline-flex items-center gap-1 rounded-full bg-[color:var(--accent-strong)] px-3 py-1 text-xs font-semibold text-white hover:opacity-90"
                    >
                      {filterT.completed}
                      <span aria-hidden="true">→</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          visibleItems.map((item) => (
            <ItemCard
              key={item.id}
              requestId={request.id}
              item={item}
              resourceName={resourceNames[item.resource_id] ?? item.resource_id}
              resource={resources.find((r) => r.id === item.resource_id)}
              highlighted={item.id === highlightId}
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
      </section>
    </div>
  );
}

function ItemCard({
  requestId,
  item,
  resourceName,
  resource,
  highlighted = false,
  isLoggedIn,
  canManage,
  canRemove,
}: {
  requestId: string;
  item: RequestItem;
  resourceName: string;
  resource?: ResourceOption;
  highlighted?: boolean;
  isLoggedIn: boolean;
  canManage: boolean;
  canRemove: boolean;
}) {
  const { dict, locale } = useI18n();
  const t = dict.requestDetail;
  const claimT = dict.claim;
  const p = item.progress;
  const target = p.target_quantity;
  const isSupply = resource?.kind === "supply";
  // Show the item's unit (e.g. "litros") after quantities so "5" reads as
  // "5 litros"; empty for countable pieces.
  const unitSuffix = item.unit ? ` ${item.unit}` : "";
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const closeItem = closeItemAction.bind(null, requestId, item.id);
  const removeItem = removeItemAction.bind(null, requestId, item.id);
  const reopenItem = reopenItemAction.bind(null, requestId, item.id);
  const itemHref = `/requests/${requestId}/items/${item.item_number}`;

  return (
    // The whole card links to the item page. A stretched overlay link covers
    // the card; the interactive controls below sit above it (`relative z-10`)
    // so the claim form and manage buttons keep working.
    <Card
      id={`item-${item.id}`}
      className={`relative scroll-mt-24 transition-shadow hover:shadow-md ${
        highlighted ? "ring-2 ring-[color:var(--accent-strong)]" : ""
      }`}
    >
      <Link
        href={itemHref}
        aria-label={`${resourceName} #${item.item_number} — ${t.viewItem}`}
        className="absolute inset-0 z-0"
      />
      <Card.Header>
        <div className="flex items-center justify-between gap-3">
          <Card.Title>{resourceName}</Card.Title>
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
            {canManage && item.status !== "open" && (
              // Undo an accidental item close (the campaign is still open).
              <form
                action={async () => {
                  await reopenItem();
                }}
              >
                <Button type="submit" size="sm">
                  {t.reopenItem}
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
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
          <ItemNumberBadge number={item.item_number} />
          <span className="text-xs text-muted">
            {t.created}: {formatItemDate(item.created_at, locale)}
          </span>
          {item.countries.length > 0 && (
            <CountryBadge
              codes={item.countries}
              onlyLabel={dict.requests.onlyCountry}
              locale={locale}
            />
          )}
        </div>
        <Card.Description>
          {t.target}: {target != null ? `${target}${unitSuffix}` : t.openEnded}
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

        {canManage && item.status === "open" && (
          <div
            className="relative z-10 mt-2 border-t pt-3"
            style={{ borderColor: "var(--card-border)" }}
          >
            <EditItemForm
              requestId={requestId}
              item={item}
              isSupply={isSupply}
              unitSuggestions={resource?.units ?? []}
            />
          </div>
        )}

        {/* Commitments are welcome even on completed/closed items — a maker
        who already has help ready can still send it. */}
        {isLoggedIn ? (
          <div className="relative z-10">
            <ClaimForm
              requestId={requestId}
              requestItemId={item.id}
              itemNumber={item.item_number}
              itemClosed={item.status !== "open"}
            />
          </div>
        ) : (
          <p className="text-muted">{claimT.loginToClaim}</p>
        )}
      </Card.Content>
    </Card>
  );
}
