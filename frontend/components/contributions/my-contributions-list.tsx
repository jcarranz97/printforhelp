"use client";

import {
  Accordion,
  Button,
  Card,
  type Key,
  ListBox,
  Select,
  toast,
} from "@heroui/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { advanceContributionAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";
import type {
  ContributionStatus,
  MyContribution,
} from "@/lib/contributions.api";

import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { ItemNumberBadge } from "@/components/requests/item-number-badge";

import { ContributionMilestones } from "./contribution-milestones";
import {
  ContributionNextStep,
  type NextStepKind,
} from "./contribution-next-step";
import { ContributionTagsForm } from "./contribution-tags-form";
import { EditQuantityForm } from "./edit-quantity-form";
import { type CenterOption, SetCenterForm } from "./set-center-form";

/** The maker-driven lifecycle advances offered on a card (forward steps plus
 * the "release" back-out). Confirm-received is a Centro action, not here. */
type AdvanceAction = "mark-prepared" | "mark-delivered" | "release";

/** URL sentinel for "no status filter", so an explicit clear survives a
 * reload instead of falling back to the default selection. */
const ALL = "all";

/**
 * The status buckets the filter offers, in lifecycle order.
 *
 * `received` is deliberately absent. The card's milestone rail stops at
 * "Entregada" — a received contribution renders identically to a delivered
 * one — so offering "Recibida" filters on a state the maker is never shown,
 * and picking it looks broken. The delivered bucket covers both.
 */
const STATUS_FILTER_ORDER = [
  "claimed",
  "prepared",
  "delivered",
  "released",
] as const;

type StatusFilterKey = (typeof STATUS_FILTER_ORDER)[number];

/** Which raw lifecycle statuses each bucket matches. */
const STATUS_FILTER_MATCHES: Record<StatusFilterKey, ContributionStatus[]> = {
  claimed: ["claimed"],
  prepared: ["prepared"],
  delivered: ["delivered", "received"],
  released: ["released"],
};

/** Legacy single-value `?status=` links: `received` folded into delivered. */
const LEGACY_STATUS_ALIASES: Record<string, StatusFilterKey> = {
  received: "delivered",
};

/** The default view: every live contribution, i.e. everything but `released`.
 * Released units went back to the pool and are the one thing a maker is done
 * with, so they stay out until asked for. Delivered ones are deliberately
 * included — dropping something off should not make it vanish from the tab. */
const DEFAULT_STATUSES: StatusFilterKey[] = [
  "claimed",
  "prepared",
  "delivered",
];

/** Parse a `?status=` value into filter keys. Accepts a comma-separated list;
 * returns null when the param is absent so the caller can apply the default. */
function parseStatusParam(raw: string | null): StatusFilterKey[] | null {
  if (raw === null) {
    return null;
  }
  if (raw === ALL) {
    return [];
  }
  const keys = raw
    .split(",")
    .map((part) => LEGACY_STATUS_ALIASES[part] ?? part)
    .filter((part): part is StatusFilterKey =>
      (STATUS_FILTER_ORDER as readonly string[]).includes(part),
    );
  return Array.from(new Set(keys));
}

/** Reflect the active filters in the URL (?part=&request=&status=&tag=) so a
 * filtered view is shareable. Uses history.replaceState so it does not re-run
 * the server component — filtering stays instant and client-side. */
function syncFilterUrl(
  part: string,
  request: string,
  status: StatusFilterKey[],
  tag: string,
): void {
  const params = new URLSearchParams();
  if (part !== ALL) {
    params.set("part", part);
  }
  if (request !== ALL) {
    params.set("request", request);
  }
  // Always written once the user touches a filter, including the ALL sentinel
  // for an empty selection: without it a shared link would silently reapply
  // the actionable default rather than the view being shared.
  params.set("status", status.length > 0 ? status.join(",") : ALL);
  if (tag !== ALL) {
    params.set("tag", tag);
  }
  const query = params.toString();
  window.history.replaceState(
    null,
    "",
    `${window.location.pathname}${query ? `?${query}` : ""}`,
  );
}

/** The maker's Contributions with their available lifecycle actions. */
export function MyContributionsList({
  contributions,
  centers,
  resourcePackaging,
}: {
  contributions: MyContribution[];
  centers: CenterOption[];
  /** Resource id → packaging instructions (Markdown), for the per-card panel. */
  resourcePackaging: Record<string, string>;
}) {
  const { dict, locale } = useI18n();
  const t = dict.myContributions;
  const searchParams = useSearchParams();

  // Distinct parts and requests the maker has contributed to, locale-sorted.
  const partOptions = useMemo(() => {
    const byId = new Map<string, string>();
    for (const c of contributions) {
      byId.set(c.resource_id, c.resource_name);
    }
    return Array.from(byId, ([id, name]) => ({ id, name })).sort((a, b) =>
      a.name.localeCompare(b.name, locale, { sensitivity: "base" }),
    );
  }, [contributions, locale]);

  const requestOptions = useMemo(() => {
    const byId = new Map<string, string>();
    for (const c of contributions) {
      byId.set(c.request_id, c.request_title);
    }
    return Array.from(byId, ([id, title]) => ({ id, title })).sort((a, b) =>
      a.title.localeCompare(b.title, locale, { sensitivity: "base" }),
    );
  }, [contributions, locale]);

  // Status buckets present in the data, in lifecycle order.
  const statusOptions = useMemo(() => {
    const present = new Set(contributions.map((c) => c.status));
    return STATUS_FILTER_ORDER.filter((key) =>
      STATUS_FILTER_MATCHES[key].some((status) => present.has(status)),
    );
  }, [contributions]);

  // Distinct maker tags across the contributions, locale-sorted.
  const tagOptions = useMemo(
    () =>
      Array.from(new Set(contributions.flatMap((c) => c.tags))).sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [contributions, locale],
  );

  // Seed each filter from the URL so shared links open pre-filtered.
  const [partFilter, setPartFilter] = useState<string>(() => {
    const value = searchParams.get("part");
    return value && contributions.some((c) => c.resource_id === value)
      ? value
      : ALL;
  });
  const [requestFilter, setRequestFilter] = useState<string>(() => {
    const value = searchParams.get("request");
    return value && contributions.some((c) => c.request_id === value)
      ? value
      : ALL;
  });
  const [statusFilter, setStatusFilter] = useState<StatusFilterKey[]>(() => {
    const fromUrl = parseStatusParam(searchParams.get("status"));
    if (fromUrl !== null) {
      return fromUrl;
    }
    // No `?status=`, so open on every live contribution. Narrowed to the
    // buckets that actually exist: a maker whose contributions are all
    // released would otherwise land on an empty list and think the tab broke.
    return DEFAULT_STATUSES.filter((key) => statusOptions.includes(key));
  });
  const [tagFilter, setTagFilter] = useState<string>(() => {
    const value = searchParams.get("tag");
    return value && contributions.some((c) => c.tags.includes(value))
      ? value
      : ALL;
  });
  const [highlightId, setHighlightId] = useState<string | null>(null);
  // Contributions the maker just advanced this session. A status change (esp.
  // "release") can push a card out of the active filter, which made it vanish
  // the instant the button was pressed — leaving no proof the action worked and
  // prompting repeat clicks. We keep these cards pinned in place, showing their
  // new state, until the view is refreshed: a reload (fresh mount clears this)
  // or any filter change (cleared below) then drops the ones that no longer
  // match, as expected.
  const [stickyIds, setStickyIds] = useState<Set<string>>(() => new Set());

  // Re-applying the filters is the moment the pinned cards should reconcile, so
  // any filter change forgets them and the pure filter takes over again.
  function clearSticky() {
    setStickyIds((prev) => (prev.size === 0 ? prev : new Set()));
  }

  // Pin a just-advanced contribution, flash it, and confirm the change with a
  // toast — so the maker sees it landed even when the card no longer matches
  // the active filter (the exact case that previously made it vanish silently).
  function markActed(id: string, action: AdvanceAction) {
    setStickyIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      return next;
    });
    setHighlightId(id);

    // The advance is deterministic, so we know the resulting status without
    // waiting for the revalidation to land.
    const acted = contributions.find((c) => c.id === id);
    const nextStatus: ContributionStatus =
      action === "release"
        ? "released"
        : action === "mark-prepared"
          ? "prepared"
          : "delivered";
    // Whether the card still belongs in the current filter afterwards; if not,
    // it is only pinned here and will leave on the next refresh — say so.
    const staysInFilter =
      acted !== undefined &&
      (partFilter === ALL || acted.resource_id === partFilter) &&
      (requestFilter === ALL || acted.request_id === requestFilter) &&
      (matchedStatuses.size === 0 || matchedStatuses.has(nextStatus)) &&
      (tagFilter === ALL || acted.tags.includes(tagFilter));

    const title =
      action === "release"
        ? t.advanceToast.released
        : action === "mark-prepared"
          ? t.advanceToast.prepared
          : t.advanceToast.delivered;
    toast(title, {
      // Forward progress reads as success; releasing (backing out) stays neutral.
      variant: action === "release" ? "default" : "success",
      description: staysInFilter ? undefined : t.advanceToast.stillShown,
    });
  }

  // Deep-link support, mirroring the comment permalinks: a
  // `#contribution-<id>` hash (e.g. from the commitments list on an item page)
  // scrolls to that card and flashes a highlight. Runs on mount and on later
  // hash changes.
  useEffect(() => {
    function applyHash() {
      const hash = window.location.hash;
      if (!hash.startsWith("#contribution-")) {
        return;
      }
      const id = hash.slice("#contribution-".length);
      setHighlightId(id);
      requestAnimationFrame(() => {
        document
          .getElementById(`contribution-${id}`)
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

  // An empty status selection means "no status filter", not "match nothing" —
  // the same thing the ALL option meant before it became multi-select.
  const matchedStatuses = useMemo(
    () => new Set(statusFilter.flatMap((key) => STATUS_FILTER_MATCHES[key])),
    [statusFilter],
  );

  const matchesFilters = useCallback(
    (c: MyContribution) =>
      (partFilter === ALL || c.resource_id === partFilter) &&
      (requestFilter === ALL || c.request_id === requestFilter) &&
      (matchedStatuses.size === 0 || matchedStatuses.has(c.status)) &&
      (tagFilter === ALL || c.tags.includes(tagFilter)),
    [partFilter, requestFilter, matchedStatuses, tagFilter],
  );

  const filtered = useMemo(
    () =>
      contributions.filter(
        (c) =>
          // A card the maker just advanced stays pinned regardless of filter,
          // so the state change is visible instead of silently disappearing.
          stickyIds.has(c.id) || matchesFilters(c),
      ),
    [contributions, matchesFilters, stickyIds],
  );

  if (contributions.length === 0) {
    return (
      <Card variant="transparent" className="py-12 text-center">
        <Card.Content>
          <p className="text-muted">{t.empty}</p>
        </Card.Content>
      </Card>
    );
  }

  function onPartChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setPartFilter(next);
    clearSticky();
    syncFilterUrl(next, requestFilter, statusFilter, tagFilter);
  }
  function onRequestChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setRequestFilter(next);
    clearSticky();
    syncFilterUrl(partFilter, next, statusFilter, tagFilter);
  }
  function onStatusChange(value: Key | Key[] | null) {
    // Multi-select hands back an array; keep it in lifecycle order so the
    // trigger and the URL read consistently regardless of click order.
    const picked = new Set(
      (Array.isArray(value) ? value : value === null ? [] : [value]).map(
        String,
      ),
    );
    const next = STATUS_FILTER_ORDER.filter((key) => picked.has(key));
    setStatusFilter(next);
    clearSticky();
    syncFilterUrl(partFilter, requestFilter, next, tagFilter);
  }
  function onTagChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setTagFilter(next);
    clearSticky();
    syncFilterUrl(partFilter, requestFilter, statusFilter, next);
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:flex-wrap sm:items-center">
        <div className="w-full sm:w-56">
          <Select
            aria-label={t.filterByPart}
            value={partFilter}
            onChange={onPartChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id={ALL} textValue={t.allParts}>
                  {t.allParts}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                {partOptions.map((part) => (
                  <ListBox.Item
                    key={part.id}
                    id={part.id}
                    textValue={part.name}
                  >
                    {part.name}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        <div className="w-full sm:w-56">
          <Select
            aria-label={t.filterByRequest}
            value={requestFilter}
            onChange={onRequestChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id={ALL} textValue={t.allRequests}>
                  {t.allRequests}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                {requestOptions.map((request) => (
                  <ListBox.Item
                    key={request.id}
                    id={request.id}
                    textValue={request.title}
                  >
                    {request.title}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        <div className="w-full sm:w-56">
          {/* Multi-select: makers routinely want "needs printing" and "needs
          dropping off" at once, which is also the default view. There is no
          "all" option — deselecting everything is the clear, and the
          placeholder then says so. */}
          <Select
            aria-label={t.statusLabel}
            selectionMode="multiple"
            placeholder={t.allStatuses}
            value={statusFilter}
            onChange={onStatusChange}
          >
            <Select.Trigger>
              <Select.Value>
                {({ defaultChildren, isPlaceholder }) => {
                  if (isPlaceholder || statusFilter.length === 0) {
                    return defaultChildren;
                  }
                  // Two joined status names overflow this control, so collapse
                  // to a count past the first.
                  return statusFilter.length === 1 ? (
                    t.statusFilter[statusFilter[0]]
                  ) : (
                    <>
                      {statusFilter.length} {t.statusesSelected}
                    </>
                  );
                }}
              </Select.Value>
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox selectionMode="multiple">
                {statusOptions.map((status) => (
                  <ListBox.Item
                    key={status}
                    id={status}
                    textValue={t.statusFilter[status]}
                  >
                    {t.statusFilter[status]}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        {tagOptions.length > 0 && (
          <div className="w-full sm:w-56">
            <Select
              aria-label={t.filterByTag}
              value={tagFilter}
              onChange={onTagChange}
            >
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Select.Popover>
                <ListBox>
                  <ListBox.Item id={ALL} textValue={t.allTags}>
                    {t.allTags}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                  {tagOptions.map((tag) => (
                    <ListBox.Item key={tag} id={tag} textValue={tag}>
                      {tag}
                      <ListBox.ItemIndicator />
                    </ListBox.Item>
                  ))}
                </ListBox>
              </Select.Popover>
            </Select>
          </div>
        )}
      </div>

      {filtered.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">{t.filteredEmpty}</p>
          </Card.Content>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          {filtered.map((c) => {
            // Supplies (any non-print_3d resource) have no "printed" step and
            // go claimed -> delivered directly; prints keep the middle step.
            const isPrint = c.resource_category === "print_3d";
            const resourceHref = isPrint
              ? `/parts/${c.resource_id}?from=contributions`
              : `/supplies/${c.resource_id}?from=contributions`;
            // A drop-off center can be set or changed any time before delivery.
            const canSetCenter =
              c.status === "claimed" || c.status === "prepared";
            // So can the amount: a maker may find they can manage more (or
            // fewer) units than they first committed to (FR-057).
            const canEditQuantity = canSetCenter;
            // Packaging guidance for this part (parts only; supplies have none).
            const packaging = resourcePackaging[c.resource_id];
            // Whether a drop-off center has been assigned yet.
            const hasCenter = c.collection_center_id !== null;
            // Delivery is the next milestone but no center is picked yet, so it
            // cannot be actioned. The center is a precondition (settable any
            // time, and changeable), not a lifecycle stage — so rather than fake
            // a milestone we state the blocker on "delivered" and point the
            // maker at the drop-off panel as the real next step.
            const deliveryBlocked =
              !hasCenter &&
              ((isPrint && c.status === "prepared") ||
                (!isPrint && c.status === "claimed"));
            // What the maker has to do next. Released contributions have no
            // next step — the bar already explains they went back to the pool.
            const nextStep: NextStepKind | null =
              c.status === "released"
                ? null
                : c.status === "delivered" || c.status === "received"
                  ? "done"
                  : isPrint && c.status === "claimed"
                    ? "print"
                    : !hasCenter
                      ? "center"
                      : "deliver";
            // The three lifecycle milestones for the progress rail. Prints go
            // claimed -> prepared("Impresa") -> delivered; supplies skip the
            // middle print step, so their rail shows just claimed -> delivered.
            const milestoneDefs = isPrint
              ? ([
                  ["claimed", c.claimed_at],
                  ["prepared", c.prepared_at],
                  ["delivered", c.delivered_at],
                ] as const)
              : ([
                  ["claimed", c.claimed_at],
                  ["delivered", c.delivered_at],
                ] as const);
            const milestones = milestoneDefs.map(([key, at]) => ({
              key,
              label: t.status[key],
              at,
            }));
            // The box is still with the maker, so a label can still be stuck
            // on it. Past this point tracking is only good for following the
            // timeline — the physical window has closed.
            const beforeHandover =
              c.status === "claimed" || c.status === "prepared";
            // The tracking panel is a permanent fixture, set up or not: it is
            // where makers learn the feature exists. The one exception is a
            // released contribution — those units went back to the pool, so
            // there is no package to label or follow.
            const showTracking = c.status !== "released";
            return (
              <Card
                key={c.id}
                id={`contribution-${c.id}`}
                className={`scroll-mt-24 transition-shadow ${
                  c.id === highlightId
                    ? "ring-2 ring-[color:var(--accent-strong)]"
                    : ""
                }`}
              >
                <Card.Content className="flex flex-col gap-3 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      {c.resource_image_url && (
                        <Link
                          href={resourceHref}
                          className="shrink-0"
                          aria-label={c.resource_name}
                        >
                          {/* External, user-supplied image URL: next/image would
                          need every host allow-listed, so a plain img is the
                          pragmatic choice here. */}
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={c.resource_image_url}
                            alt={c.resource_name}
                            className="h-16 w-16 rounded-lg object-cover"
                          />
                        </Link>
                      )}
                      <div className="flex flex-col gap-0.5">
                        <span className="flex items-center gap-2">
                          <Link
                            href={`/requests/${c.request_id}/items/${c.item_number}`}
                            className="font-semibold hover:underline"
                          >
                            {c.resource_name}
                          </Link>
                          <ItemNumberBadge number={c.item_number} />
                        </span>
                        <Link
                          href={`/requests/${c.request_id}?from=contributions`}
                          className="text-xs text-muted hover:underline"
                        >
                          {t.fromRequest} {c.request_title}
                        </Link>
                      </div>
                    </div>
                    <div className="w-full sm:w-auto sm:max-w-[60%]">
                      <ContributionTagsForm
                        contributionId={c.id}
                        tags={c.tags}
                        allTags={tagOptions}
                      />
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-col gap-1 text-sm">
                      <EditQuantityForm
                        contributionId={c.id}
                        quantity={c.quantity}
                        unit={c.item_unit}
                        requestId={c.request_id}
                        itemNumber={c.item_number}
                        canEdit={canEditQuantity}
                        hasTracking={c.tracking_token !== null}
                      />
                      {/* Status is conveyed by the milestone bar below; only
                      the auto-received note stays inline here. */}
                      {c.auto_received && (
                        <span className="text-xs text-muted">
                          {t.autoReceived}
                        </span>
                      )}
                    </div>
                    {/* Forward actions live in the next-step box below; only
                    "Release" (backing out) stays up here. */}
                    <div className="flex flex-wrap gap-2">
                      {(c.status === "claimed" || c.status === "prepared") && (
                        <ActionButton
                          id={c.id}
                          action="release"
                          label={t.release}
                          variant="secondary"
                          onActed={markActed}
                        />
                      )}
                    </div>
                  </div>

                  {(c.status === "claimed" || c.status === "prepared") && (
                    <p className="text-xs text-muted">{t.releaseHint}</p>
                  )}

                  {/* Milestone bar (design 1b): the lifecycle as a filled rail
                  with a node + timestamp per step and the next step pulsing.
                  Sits up top since it now carries the status the old chip
                  showed. */}
                  <div
                    className="border-t pt-3"
                    style={{ borderColor: "var(--card-border)" }}
                  >
                    <ContributionMilestones
                      steps={milestones}
                      released={c.status === "released"}
                      releasedAt={c.released_at}
                      blockedLabel={
                        deliveryBlocked ? t.milestoneNeedsCenter : null
                      }
                    />
                  </div>

                  {/* What to do now, with the action attached: the rail says
                  where you are, this says what's next. */}
                  {nextStep && (
                    <ContributionNextStep
                      kind={nextStep}
                      detail={
                        nextStep === "deliver"
                          ? c.collection_center_name
                          : nextStep === "center"
                            ? t.nextStepCenterHint
                            : null
                      }
                      action={
                        nextStep === "print" ? (
                          <ActionButton
                            id={c.id}
                            action="mark-prepared"
                            label={t.markPrinted}
                            onActed={markActed}
                          />
                        ) : nextStep === "deliver" ? (
                          <ActionButton
                            id={c.id}
                            action="mark-delivered"
                            label={t.markDelivered}
                            onActed={markActed}
                          />
                        ) : null
                      }
                    />
                  )}

                  {/* Tracking labels, the drop-off center (shows where the part
                  was left, plus the picker while it can still change) and the
                  part's packaging instructions (collapsed, for a quick re-check
                  before shipping) folded into one accordion, matching the
                  request item cards. */}
                  {(hasCenter || canSetCenter || packaging || showTracking) && (
                    <div
                      className="border-t pt-3"
                      style={{ borderColor: "var(--card-border)" }}
                    >
                      <Accordion
                        allowsMultipleExpanded
                        // Tracking leads while the labels can still go on the
                        // box — that is the whole reason it sits above the
                        // drop-off panel. Once handed over it folds away: the
                        // timeline is a lookup, not a task.
                        defaultExpandedKeys={
                          showTracking && beforeHandover
                            ? ["tracking", "center"]
                            : ["center"]
                        }
                        className="w-full"
                      >
                        {/* Deliberately an illustration and NOT the real QR:
                        makers were screenshotting the thumbnail to stick on
                        their boxes, which yields one low-res group code instead
                        of the printable label sheet. Nothing scannable on this
                        card — labels come from the download on the manage
                        page. */}
                        {showTracking && (
                          <Accordion.Item id="tracking">
                            <Accordion.Heading>
                              <Accordion.Trigger>
                                {t.trackingHeading}
                                <Accordion.Indicator />
                              </Accordion.Trigger>
                            </Accordion.Heading>
                            <Accordion.Panel>
                              <Accordion.Body className="flex items-start gap-4">
                                {/* Decorative: the copy beside it carries the
                                meaning, so it stays out of the a11y tree. The
                                art is black line work on white, hence the
                                explicit light background in both themes. */}
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img
                                  src="/illustrations/qr-scanning.png"
                                  alt=""
                                  aria-hidden="true"
                                  className="h-24 w-24 shrink-0 rounded-lg border border-[var(--card-border)] bg-white"
                                />
                                <div className="flex flex-col gap-2">
                                  <p className="text-sm text-muted">
                                    {/* Not set up yet → what it buys you. Set
                                    up and still holding the box → go print the
                                    labels. Already handed over → "stick this on
                                    it" is advice for a moment that has passed,
                                    so the QR is just how you follow along. */}
                                    {c.tracking_token === null
                                      ? t.trackingNotSetBody
                                      : beforeHandover
                                        ? t.trackingHasBody
                                        : t.trackingHasBodyAfter}
                                  </p>
                                  <Link
                                    href={`/my-contributions/${c.id}/tracking`}
                                    className="text-sm font-medium text-[var(--accent-strong)] hover:underline"
                                  >
                                    {c.tracking_token === null
                                      ? t.trackingSetupLink
                                      : t.trackingManageLink}
                                  </Link>
                                </div>
                              </Accordion.Body>
                            </Accordion.Panel>
                          </Accordion.Item>
                        )}
                        {(hasCenter || canSetCenter) && (
                          <Accordion.Item id="center">
                            <Accordion.Heading>
                              <Accordion.Trigger>
                                {t.dropOffHeading}
                                <Accordion.Indicator />
                              </Accordion.Trigger>
                            </Accordion.Heading>
                            <Accordion.Panel>
                              <Accordion.Body className="flex flex-col gap-2">
                                {/* Where the part was (or will be) left. */}
                                {hasCenter ? (
                                  <span className="flex flex-wrap items-center gap-2 text-sm">
                                    <Link
                                      href={`/centers/${c.collection_center_id}?from=contributions`}
                                      className="font-medium hover:underline"
                                    >
                                      {t.dropOffAt} {c.collection_center_name}
                                    </Link>
                                    {c.collection_center_location_url && (
                                      <a
                                        href={c.collection_center_location_url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
                                      >
                                        {t.getDirections}
                                        <span aria-hidden="true"> ↗</span>
                                      </a>
                                    )}
                                  </span>
                                ) : (
                                  <span className="text-xs text-muted">
                                    {t.noCenterYet}
                                  </span>
                                )}
                                {canSetCenter && (
                                  <SetCenterForm
                                    contributionId={c.id}
                                    centers={centers}
                                    currentCenterId={
                                      c.collection_center_id ?? undefined
                                    }
                                    preferredCenterIds={
                                      c.preferred_collection_center_ids
                                    }
                                    hasCenter={c.collection_center_id !== null}
                                    hideLabel
                                  />
                                )}
                              </Accordion.Body>
                            </Accordion.Panel>
                          </Accordion.Item>
                        )}
                        {packaging && (
                          <Accordion.Item id="packaging">
                            <Accordion.Heading>
                              <Accordion.Trigger>
                                {dict.requestItem.packagingHeading}
                                <Accordion.Indicator />
                              </Accordion.Trigger>
                            </Accordion.Heading>
                            <Accordion.Panel>
                              <Accordion.Body>
                                <CollapsibleMarkdown source={packaging} />
                              </Accordion.Body>
                            </Accordion.Panel>
                          </Accordion.Item>
                        )}
                      </Accordion>
                    </div>
                  )}
                </Card.Content>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ActionButton({
  id,
  action,
  label,
  variant,
  onActed,
}: {
  id: string;
  action: AdvanceAction;
  label: string;
  variant?: "secondary";
  /** Called once the advance succeeds, so the card can be pinned and confirmed. */
  onActed: (id: string, action: AdvanceAction) => void;
}) {
  const boundAction = advanceContributionAction.bind(null, id, action, null);
  return (
    <form
      action={async () => {
        const result = await boundAction();
        // Only confirm on success — a failed advance leaves the card as-is.
        if (!result?.error) {
          onActed(id, action);
        }
      }}
    >
      <Button type="submit" size="sm" variant={variant}>
        {label}
      </Button>
    </form>
  );
}
