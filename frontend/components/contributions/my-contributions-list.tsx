"use client";

import { Button, Card, Chip, type Key, ListBox, Select } from "@heroui/react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { advanceContributionAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";
import type {
  ContributionStatus,
  MyContribution,
} from "@/lib/contributions.api";

import { ContributionTagsForm } from "./contribution-tags-form";
import { type CenterOption, SetCenterForm } from "./set-center-form";

const ALL = "all";

const STATUS_COLOR: Record<
  ContributionStatus,
  "default" | "success" | "warning"
> = {
  claimed: "default",
  prepared: "default",
  delivered: "success",
  received: "success",
  released: "warning",
};

/** Lifecycle order, used to sort the status filter options. */
const STATUS_ORDER: ContributionStatus[] = [
  "claimed",
  "prepared",
  "delivered",
  "received",
  "released",
];

/** Reflect the active filters in the URL (?part=&request=&status=&tag=) so a
 * filtered view is shareable. Uses history.replaceState so it does not re-run
 * the server component — filtering stays instant and client-side. */
function syncFilterUrl(
  part: string,
  request: string,
  status: string,
  tag: string,
): void {
  const params = new URLSearchParams();
  if (part !== ALL) {
    params.set("part", part);
  }
  if (request !== ALL) {
    params.set("request", request);
  }
  if (status !== ALL) {
    params.set("status", status);
  }
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

/** Format a contribution lifecycle timestamp for the card timeline. */
function formatDateTime(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** The maker's Contributions with their available lifecycle actions. */
export function MyContributionsList({
  contributions,
  centers,
}: {
  contributions: MyContribution[];
  centers: CenterOption[];
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

  // Statuses present in the data, in lifecycle order.
  const statusOptions = useMemo(() => {
    const present = new Set(contributions.map((c) => c.status));
    return STATUS_ORDER.filter((s) => present.has(s));
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
  const [statusFilter, setStatusFilter] = useState<string>(() => {
    const value = searchParams.get("status");
    return value && STATUS_ORDER.includes(value as ContributionStatus)
      ? value
      : ALL;
  });
  const [tagFilter, setTagFilter] = useState<string>(() => {
    const value = searchParams.get("tag");
    return value && contributions.some((c) => c.tags.includes(value))
      ? value
      : ALL;
  });

  const filtered = useMemo(
    () =>
      contributions.filter(
        (c) =>
          (partFilter === ALL || c.resource_id === partFilter) &&
          (requestFilter === ALL || c.request_id === requestFilter) &&
          (statusFilter === ALL || c.status === statusFilter) &&
          (tagFilter === ALL || c.tags.includes(tagFilter)),
      ),
    [contributions, partFilter, requestFilter, statusFilter, tagFilter],
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
    syncFilterUrl(next, requestFilter, statusFilter, tagFilter);
  }
  function onRequestChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setRequestFilter(next);
    syncFilterUrl(partFilter, next, statusFilter, tagFilter);
  }
  function onStatusChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setStatusFilter(next);
    syncFilterUrl(partFilter, requestFilter, next, tagFilter);
  }
  function onTagChange(value: Key | null) {
    const next = value === null ? ALL : String(value);
    setTagFilter(next);
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
          <Select
            aria-label={t.statusLabel}
            value={statusFilter}
            onChange={onStatusChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id={ALL} textValue={t.allStatuses}>
                  {t.allStatuses}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
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
            // A drop-off center can be set or changed any time before delivery.
            const canSetCenter =
              c.status === "claimed" || c.status === "prepared";
            // Lifecycle timestamps that have happened, in chronological order.
            const timeline = (
              [
                ["claimed", c.claimed_at],
                ["prepared", c.prepared_at],
                ["delivered", c.delivered_at],
                ["received", c.received_at],
                ["released", c.released_at],
              ] as const
            ).filter(
              (entry): entry is [ContributionStatus, string] => !!entry[1],
            );
            return (
              <Card key={c.id}>
                <Card.Content className="flex flex-col gap-3 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      {c.resource_image_url && (
                        <Link
                          href={`/parts/${c.resource_id}?from=contributions`}
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
                        <Link
                          href={`/parts/${c.resource_id}?from=contributions`}
                          className="font-semibold hover:underline"
                        >
                          {c.resource_name}
                        </Link>
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
                      <span>
                        {t.quantity}: <strong>{c.quantity}</strong>
                      </span>
                      <Chip
                        color={STATUS_COLOR[c.status]}
                        variant="soft"
                        size="sm"
                      >
                        {t.status[c.status]}
                      </Chip>
                      {c.collection_center_id === null ? (
                        <span className="text-xs text-muted">
                          {t.noCenterYet}
                        </span>
                      ) : (
                        <Link
                          href={`/centers/${c.collection_center_id}?from=contributions`}
                          className="text-xs text-muted hover:underline"
                        >
                          {t.dropOffAt} {c.collection_center_name}
                        </Link>
                      )}
                      {c.auto_received && (
                        <span className="text-xs text-muted">
                          {t.autoReceived}
                        </span>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {c.status === "claimed" && (
                        <ActionButton
                          id={c.id}
                          action="mark-prepared"
                          label={t.markPrinted}
                        />
                      )}
                      {c.status === "prepared" &&
                        c.collection_center_id !== null && (
                          <ActionButton
                            id={c.id}
                            action="mark-delivered"
                            label={t.markDelivered}
                          />
                        )}
                      {(c.status === "claimed" || c.status === "prepared") && (
                        <ActionButton
                          id={c.id}
                          action="release"
                          label={t.release}
                          variant="secondary"
                        />
                      )}
                    </div>
                  </div>

                  {canSetCenter && (
                    <div
                      className="border-t pt-3"
                      style={{ borderColor: "var(--card-border)" }}
                    >
                      <SetCenterForm
                        contributionId={c.id}
                        centers={centers}
                        currentCenterId={c.collection_center_id ?? undefined}
                        hasCenter={c.collection_center_id !== null}
                      />
                    </div>
                  )}

                  <div
                    className="flex flex-col gap-0.5 border-t pt-3 text-xs text-muted"
                    style={{ borderColor: "var(--card-border)" }}
                  >
                    {timeline.map(([key, at]) => (
                      <span key={key}>
                        {t.status[key]}: {formatDateTime(at, locale)}
                      </span>
                    ))}
                  </div>

                  <div
                    className="border-t pt-3"
                    style={{ borderColor: "var(--card-border)" }}
                  >
                    <Link
                      href={`/my-contributions/${c.id}/tracking`}
                      className="text-sm font-medium text-[var(--accent-strong)] hover:underline"
                    >
                      {c.tracking_token ? t.trackingView : t.trackingSetup}
                    </Link>
                  </div>
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
}: {
  id: string;
  action: "mark-prepared" | "mark-delivered" | "release";
  label: string;
  variant?: "secondary";
}) {
  const boundAction = advanceContributionAction.bind(null, id, action, null);
  return (
    <form
      action={async () => {
        await boundAction();
      }}
    >
      <Button type="submit" size="sm" variant={variant}>
        {label}
      </Button>
    </form>
  );
}
