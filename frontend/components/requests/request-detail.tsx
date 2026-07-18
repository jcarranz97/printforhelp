"use client";

import { Accordion, Button, Card, Chip, type Key } from "@heroui/react";
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
import { SourceLinkButton } from "@/components/resources/source-link-button";
import { BANNER_ASPECT_CSS } from "@/components/requests/request-image-field";
import { EntityFeed, type FeedViewer } from "@/components/comments/entity-feed";
import { LikeButton } from "@/components/reactions/like-button";
import { useI18n } from "@/i18n/provider";
import type { ActivityEntry, Comment } from "@/lib/feed.api";
import type { ResourceOption } from "@/lib/resource-options";
import { deriveItemState } from "@/lib/request-item-state";
import type {
  HelpState,
  ItemCommitment,
  RequestDetail,
  RequestItem,
} from "@/lib/requests.api";

const FILTER_KEYS = ["all", "needs_help", "completed"] as const;
type ItemFilter = (typeof FILTER_KEYS)[number];

import { AddItemForm } from "./add-item-form";
import { ClaimForm } from "./claim-form";
import { CommitmentsDisclosure } from "./commitments-disclosure";
import { CopyLinkButton } from "./copy-link-button";
import { CountryBadge } from "./country-badge";
import { EditItemForm } from "./edit-item-form";
import { ItemNumberBadge } from "./item-number-badge";
import {
  type ItemCenter,
  ItemPreferredCenters,
} from "./item-preferred-centers";
import { ItemProgress } from "./item-progress";

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
  resourceSources,
  resourceImages,
  resourcePackaging,
  centerCandidates,
  commitmentsByItem,
  commentsByItem,
  activityByItem,
  viewer,
  currentUsername,
  isLoggedIn,
  canManage,
  initialWatching,
  itemReactions,
}: {
  request: RequestDetail;
  resources: ResourceOption[];
  resourceNames: Record<string, string>;
  /** Resource id → external source/download URL, for the per-item CTA. */
  resourceSources: Record<string, string>;
  /** Resource id → catalog image URL, for the per-item part preview. */
  resourceImages: Record<string, string>;
  /** Resource id → packaging instructions (Markdown), for the per-item card. */
  resourcePackaging: Record<string, string>;
  /** The request's preferred drop-off centers, resolved to full details; the
   * candidate set every item's "drop-off centers" panel filters down from. */
  centerCandidates: ItemCenter[];
  /** Item id → its public commitments, so each card lists them inline. */
  commitmentsByItem: Record<string, ItemCommitment[]>;
  /** Item id → its comment thread (entity type "request_item"). */
  commentsByItem: Record<string, Comment[]>;
  /** Item id → its activity timeline (entity type "request_item"). */
  activityByItem: Record<string, ActivityEntry[]>;
  /** Viewer identity for the per-item comment composer/edit controls. */
  viewer: FeedViewer;
  /** Viewer's username, so their own commitments offer an edit shortcut. */
  currentUsername: string | null;
  isLoggedIn: boolean;
  canManage: boolean;
  initialWatching: boolean;
  /** Item id → its reaction (like) state, for the per-item heart. */
  itemReactions: Record<string, { count: number; reacted: boolean }>;
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
  // Item whose "Comments & activity" panel a comment permalink asked to open,
  // and the comment to highlight inside it.
  const [openFeedId, setOpenFeedId] = useState<string | null>(null);
  const [feedCommentId, setFeedCommentId] = useState<string | null>(null);
  // Activity (status-change) entry a "changed the status" notification asked to
  // highlight inside an item's feed panel.
  const [feedRecordId, setFeedRecordId] = useState<string | null>(null);

  // Deep-link support. Two shapes land here:
  //  - `#item-<id>`  — a notification for a newly added item: switch to "All"
  //    (so the item shows regardless of its help-state bucket), scroll, flash.
  //  - `#comment-<id>` — a copied comment permalink: the comment lives in one
  //    item's feed, which is collapsed by default, so a plain scroll hits a
  //    hidden (layout-less) node and fails. Find the owning item, reveal it,
  //    open its feed panel, then scroll to the comment once it has layout.
  // Runs on mount and on later hash changes (same-page navigations).
  useEffect(() => {
    // A deep link is strictly one-shot per tab. Stripping the URL is not enough:
    // in a production build Next's Router Cache restores the stale fragment when
    // the user returns to this campaign from the directory, which would re-fire
    // the effect and yank them back to the comment. So we record consumed
    // fragments in sessionStorage and ignore any we have already handled.
    const CONSUMED_KEY = "pforh:consumed-deeplinks";
    function isConsumed(hash: string): boolean {
      try {
        const raw = sessionStorage.getItem(CONSUMED_KEY);
        return raw ? (JSON.parse(raw) as string[]).includes(hash) : false;
      } catch {
        return false;
      }
    }
    function markConsumed(hash: string): void {
      try {
        const raw = sessionStorage.getItem(CONSUMED_KEY);
        const arr = raw ? (JSON.parse(raw) as string[]) : [];
        if (!arr.includes(hash)) {
          arr.push(hash);
          sessionStorage.setItem(CONSUMED_KEY, JSON.stringify(arr));
        }
      } catch {
        // sessionStorage unavailable (private mode): a return visit just
        // re-scrolls, the pre-fix behavior — never worse.
      }
    }
    function stripHash(): void {
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    }
    function applyHash() {
      const hash = window.location.hash;
      if (
        !hash.startsWith("#item-") &&
        !hash.startsWith("#comment-") &&
        !hash.startsWith("#record-")
      ) {
        return;
      }
      // Already handled in this tab — a router-cache restore on return, a
      // refresh, or a same-page re-navigation. Do nothing but tidy the URL.
      if (isConsumed(hash)) {
        stripHash();
        return;
      }
      if (hash.startsWith("#item-")) {
        const id = hash.slice("#item-".length);
        setFilter("all");
        setHighlightId(id);
        requestAnimationFrame(() => {
          document
            .getElementById(`item-${id}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
        });
        markConsumed(hash);
        stripHash();
        return;
      }
      if (hash.startsWith("#record-")) {
        // A "changed the status" notification: the status entry lives in one
        // item's feed (hidden by default in commentsOnly mode). Find the owning
        // item, reveal it, open its feed, then scroll to and highlight the entry
        // once it has layout — EntityFeed surfaces it via deepLinkRecordId.
        const recordId = hash.slice("#record-".length);
        const owner = request.items.find((it) =>
          (activityByItem[it.id] ?? []).some((a) => a.id === recordId),
        );
        if (!owner) {
          // A campaign-level status entry: the always-visible feed handles it.
          return;
        }
        setFilter("all");
        setOpenFeedId(owner.id);
        setFeedRecordId(recordId);
        setFeedCommentId(null);
        window.setTimeout(() => {
          document
            .getElementById(`record-${recordId}`)
            ?.scrollIntoView({ behavior: "smooth", block: "center" });
        }, 400);
        markConsumed(hash);
        stripHash();
        return;
      }
      const commentId = hash.slice("#comment-".length);
      const owner = request.items.find((it) =>
        (commentsByItem[it.id] ?? []).some((c) => c.id === commentId),
      );
      if (!owner) {
        // A campaign-level comment: the always-visible feed below handles it.
        return;
      }
      setFilter("all");
      setOpenFeedId(owner.id);
      setFeedCommentId(commentId);
      setFeedRecordId(null);
      // Let the card render and its feed panel animate open, then bring the
      // comment into view. EntityFeed highlights it via deepLinkCommentId.
      window.setTimeout(() => {
        document
          .getElementById(`comment-${commentId}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 400);
      markConsumed(hash);
      stripHash();
    }
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, [request.items, commentsByItem, activityByItem]);

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
              sourceUrl={resourceSources[item.resource_id]}
              imageUrl={resourceImages[item.resource_id]}
              packagingInstructions={resourcePackaging[item.resource_id]}
              centerCandidates={centerCandidates}
              commitments={commitmentsByItem[item.id] ?? []}
              comments={commentsByItem[item.id] ?? []}
              activity={activityByItem[item.id] ?? []}
              reaction={itemReactions[item.id]}
              viewer={viewer}
              currentUsername={currentUsername}
              highlighted={item.id === highlightId}
              feedOpen={item.id === openFeedId}
              deepLinkCommentId={item.id === openFeedId ? feedCommentId : null}
              deepLinkRecordId={item.id === openFeedId ? feedRecordId : null}
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
  sourceUrl,
  imageUrl,
  packagingInstructions,
  centerCandidates,
  commitments,
  comments,
  activity,
  reaction,
  viewer,
  currentUsername,
  highlighted = false,
  feedOpen = false,
  deepLinkCommentId = null,
  deepLinkRecordId = null,
  isLoggedIn,
  canManage,
  canRemove,
}: {
  requestId: string;
  item: RequestItem;
  resourceName: string;
  resource?: ResourceOption;
  /** External source/download URL of the item's resource, if any. */
  sourceUrl?: string;
  /** Catalog image URL of the item's resource, if any. */
  imageUrl?: string;
  /** Packaging instructions (Markdown) from the item's resource, if any. */
  packagingInstructions?: string;
  /** The request's preferred centers; the panel filters to this item's subset. */
  centerCandidates: ItemCenter[];
  /** This item's public commitments. */
  commitments: ItemCommitment[];
  /** This item's comment thread (entity type "request_item"). */
  comments: Comment[];
  /** This item's activity timeline (entity type "request_item"). */
  activity: ActivityEntry[];
  /** This item's reaction (like) state; undefined falls back to zero. */
  reaction?: { count: number; reacted: boolean };
  /** Viewer identity for the comment composer/edit controls. */
  viewer: FeedViewer;
  /** Viewer's username, so their own commitments offer an edit shortcut. */
  currentUsername: string | null;
  highlighted?: boolean;
  /** A comment permalink targeted this item: open its feed panel on arrival. */
  feedOpen?: boolean;
  /** Comment to highlight in this item's feed (parent-owned deep link); null
   * when no permalink targets this item, which also tells EntityFeed not to
   * read the URL hash itself. */
  deepLinkCommentId?: string | null;
  /** Status-change entry to reveal + highlight in this item's feed (parent-owned
   * deep link); null when no status notification targets this item. */
  deepLinkRecordId?: string | null;
  isLoggedIn: boolean;
  canManage: boolean;
  canRemove: boolean;
}) {
  const { dict, locale } = useI18n();
  const t = dict.requestDetail;
  const itemT = dict.requestItem;
  const claimT = dict.claim;
  const p = item.progress;
  const target = p.target_quantity;
  const isSupply = resource?.kind === "supply";
  // Show the item's unit (e.g. "litros") after quantities so "5" reads as
  // "5 litros"; empty for countable pieces.
  const unitSuffix = item.unit ? ` ${item.unit}` : "";
  const closeItem = closeItemAction.bind(null, requestId, item.id);
  const removeItem = removeItemAction.bind(null, requestId, item.id);
  const reopenItem = reopenItemAction.bind(null, requestId, item.id);

  // The card accordion is controlled so a comment permalink can pop the feed
  // panel open. "contribute" starts open (primary action); when a permalink
  // targets this item (`feedOpen`), add "feed" without collapsing the rest.
  const [expandedKeys, setExpandedKeys] = useState<Set<Key>>(
    () => new Set<Key>(["contribute"]),
  );
  useEffect(() => {
    if (feedOpen) {
      setExpandedKeys((prev) => new Set(prev).add("feed"));
    }
  }, [feedOpen]);

  return (
    // Everything a maker needs — packaging, drop-off centers, and the current
    // commitments — now lives on this card, so it no longer links out to the
    // per-item page.
    <Card
      id={`item-${item.id}`}
      className={`relative scroll-mt-24 ${
        highlighted ? "ring-2 ring-[color:var(--accent-strong)]" : ""
      }`}
    >
      <Card.Header>
        <div className="flex items-center justify-between gap-3">
          <Card.Title>{resourceName}</Card.Title>
          <div className="relative z-10 flex items-center gap-2">
            <LikeButton
              entityType="request_item"
              entityId={item.id}
              initialCount={reaction?.count ?? 0}
              initialReacted={reaction?.reacted ?? false}
              isAuthenticated={isLoggedIn}
            />
            {/* Share this exact part: opens the campaign and highlights it.
            Sits before the manage controls; the friendly nudge is its tooltip. */}
            <CopyLinkButton path={`/requests/${requestId}#item-${item.id}`} />
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
      </Card.Header>
      <Card.Content className="flex flex-col gap-3 text-sm">
        {/* Part preview on the left, the item meta (number, date, country,
        target) + MakerWorld CTA on the right, so a maker sees what they'd be
        printing right next to its details. Stacks on narrow screens. A plain
        img avoids next/image host allow-listing, matching the catalog cards. */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
          {imageUrl && (
            <img
              src={imageUrl}
              alt={resourceName}
              className="w-full rounded-xl object-cover sm:w-48 sm:shrink-0"
            />
          )}
          <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
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
            <p className="text-sm text-muted">
              {t.target}:{" "}
              {target != null ? `${target}${unitSuffix}` : t.openEnded}
            </p>
            {/* Quick access to the file/link so a maker can grab it without
            opening the item page. A friendly nudge frames it as a way to
            decide how many they can take on; the button sits above the card
            (relative z-10) while the text keeps the card clickable. */}
            {sourceUrl && (
              <div className="self-start">
                <p className="mb-1 text-xs text-muted">{t.viewPartPrompt}</p>
                <div className="relative z-10">
                  <SourceLinkButton url={sourceUrl} />
                </div>
              </div>
            )}
          </div>
        </div>
        <ItemProgress p={p} unit={item.unit} />

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

        {/* One accordion for the whole card so every panel reads the same:
        packaging + drop-off centers (reference detail from the retired item
        page), the contribute form (open by default — it's the primary action),
        and the ask-and-coordinate comment thread. `relative z-10` keeps the
        interactive panels above the card. */}
        <div className="relative z-10">
          <Accordion
            allowsMultipleExpanded
            expandedKeys={expandedKeys}
            onExpandedChange={setExpandedKeys}
            className="w-full"
          >
            {packagingInstructions && (
              <Accordion.Item id="packaging">
                <Accordion.Heading>
                  <Accordion.Trigger>
                    {itemT.packagingHeading}
                    <Accordion.Indicator />
                  </Accordion.Trigger>
                </Accordion.Heading>
                <Accordion.Panel>
                  <Accordion.Body>
                    <CollapsibleMarkdown source={packagingInstructions} />
                  </Accordion.Body>
                </Accordion.Panel>
              </Accordion.Item>
            )}
            {centerCandidates.length > 0 && (
              <Accordion.Item id="centers">
                <Accordion.Heading>
                  <Accordion.Trigger>
                    {itemT.centersHeading}
                    <Accordion.Indicator />
                  </Accordion.Trigger>
                </Accordion.Heading>
                <Accordion.Panel>
                  <Accordion.Body>
                    <ItemPreferredCenters
                      requestId={requestId}
                      itemId={item.id}
                      candidates={centerCandidates}
                      selectedIds={item.preferred_collection_center_ids}
                      canManage={canManage}
                      hideHeading
                    />
                  </Accordion.Body>
                </Accordion.Panel>
              </Accordion.Item>
            )}

            {/* Commitments are welcome even on completed/closed items — a maker
            who already has help ready can still send it. */}
            <Accordion.Item id="contribute">
              <Accordion.Heading>
                <Accordion.Trigger>
                  {claimT.heading}
                  <Accordion.Indicator />
                </Accordion.Trigger>
              </Accordion.Heading>
              <Accordion.Panel>
                <Accordion.Body>
                  {isLoggedIn ? (
                    <ClaimForm
                      requestId={requestId}
                      requestItemId={item.id}
                      itemNumber={item.item_number}
                      itemClosed={item.status !== "open"}
                      sourceUrl={sourceUrl}
                      remaining={p.remaining}
                      committed={p.committed_quantity}
                      target={p.target_quantity}
                      contributorCount={p.contributor_count}
                      commitments={commitments}
                      currentUsername={currentUsername}
                      embedded
                    />
                  ) : (
                    <div className="flex flex-col gap-3">
                      <p className="text-muted">{claimT.loginToClaim}</p>
                      <CommitmentsDisclosure
                        commitments={commitments}
                        currentUsername={currentUsername}
                      />
                    </div>
                  )}
                </Accordion.Body>
              </Accordion.Panel>
            </Accordion.Item>

            <Accordion.Item id="feed">
              <Accordion.Heading>
                <Accordion.Trigger>
                  {itemT.feedTitle} ({comments.length})
                  <Accordion.Indicator />
                </Accordion.Trigger>
              </Accordion.Heading>
              <Accordion.Panel>
                <Accordion.Body className="flex flex-col gap-3">
                  <p className="text-xs text-muted">{itemT.feedSubtitle}</p>
                  <EntityFeed
                    revalidate={`/requests/${requestId}`}
                    entityType="request_item"
                    entityId={item.id}
                    comments={comments}
                    activity={activity}
                    viewer={viewer}
                    deepLinkCommentId={deepLinkCommentId}
                    deepLinkRecordId={deepLinkRecordId}
                    commentsOnly
                  />
                </Accordion.Body>
              </Accordion.Panel>
            </Accordion.Item>
          </Accordion>
        </div>
      </Card.Content>
    </Card>
  );
}
