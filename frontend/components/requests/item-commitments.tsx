"use client";

import { Checkbox, Chip, type Key, ListBox, Select } from "@heroui/react";
import Link from "next/link";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";
import type { ContributionStatus, ItemCommitment } from "@/lib/requests.api";

const STATUS_COLOR: Record<
  ContributionStatus,
  "default" | "success" | "warning"
> = {
  claimed: "default",
  prepared: "default",
  delivered: "warning",
  received: "success",
  released: "warning",
};

// Sentinel option ids for the center filter. Real center names can never
// collide with these because they are wrapped in angle brackets.
const ALL_CENTERS = "<all>";
const NO_CENTER = "<none>";

/**
 * Timestamp of the commitment's current lifecycle stage, so readers can see
 * how recently each maker moved it forward. Falls back to earlier stamps if a
 * later one is somehow missing.
 */
function statusDate(c: ItemCommitment): string {
  switch (c.status) {
    case "received":
      return c.received_at ?? c.delivered_at ?? c.prepared_at ?? c.claimed_at;
    case "delivered":
      return c.delivered_at ?? c.prepared_at ?? c.claimed_at;
    case "prepared":
      return c.prepared_at ?? c.claimed_at;
    default:
      return c.claimed_at;
  }
}

/** Format a lifecycle timestamp as a short, locale-aware date. */
function formatStatusDate(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleDateString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * Public list of commitments on a request item: who has already committed,
 * how many, and where they are in the lifecycle. Notes/tags are private and
 * never shown here. Reads are public so the shareable link is transparent.
 */
export function ItemCommitments({
  commitments,
  currentUsername = null,
}: {
  commitments: ItemCommitment[];
  /** Viewer's username, so their own commitments offer an edit shortcut. */
  currentUsername?: string | null;
}) {
  const { dict, locale } = useI18n();
  const t = dict.requestItem;

  // Released commitments are back-out signals, not real progress — showing
  // them here only confuses readers, so keep them out of the public list.
  const visibleCommitments = commitments.filter((c) => c.status !== "released");

  // Distinct centers that some visible commitment targets, plus whether any
  // commitment has no center yet (which gets its own "No center" filter row).
  const { centerOptions, hasUnassigned } = useMemo(() => {
    const names = new Set<string>();
    let unassigned = false;
    for (const c of commitments) {
      if (c.status === "released") continue;
      if (c.collection_center_name) names.add(c.collection_center_name);
      else unassigned = true;
    }
    return {
      centerOptions: Array.from(names).sort((a, b) => a.localeCompare(b)),
      hasUnassigned: unassigned,
    };
  }, [commitments]);

  // Selected filter values (center names and/or the NO_CENTER sentinel). Empty
  // means "all centers" — no filter applied.
  const [centerFilter, setCenterFilter] = useState<string[]>([]);
  // "Only my contributions" — offered only to a logged-in viewer.
  const [onlyMine, setOnlyMine] = useState(false);

  // The Select is controlled with an explicit "All centers" row, so when no
  // filter is active that row is what shows as checked.
  const selectValue = centerFilter.length === 0 ? [ALL_CENTERS] : centerFilter;

  function onCenterChange(value: Key | Key[] | null) {
    const picked = value === null ? [] : Array.isArray(value) ? value : [value];
    const next = new Set(picked.map(String));
    // Clicking "All centers" (adding it) resets the filter; any other change
    // just drops that reset row and keeps the real picks.
    const allJustClicked = next.has(ALL_CENTERS) && centerFilter.length > 0;
    if (allJustClicked) {
      setCenterFilter([]);
      return;
    }
    next.delete(ALL_CENTERS);
    setCenterFilter(Array.from(next));
  }

  const filteredCommitments = visibleCommitments
    .filter((c) => {
      if (onlyMine && c.maker_username !== currentUsername) {
        return false;
      }
      if (centerFilter.length > 0) {
        const matchesCenter =
          c.collection_center_name === null
            ? centerFilter.includes(NO_CENTER)
            : centerFilter.includes(c.collection_center_name);
        if (!matchesCenter) {
          return false;
        }
      }
      return true;
    })
    // Most recently touched first, regardless of stage, so the freshest
    // activity is always on top.
    .sort(
      (a, b) =>
        new Date(statusDate(b)).getTime() - new Date(statusDate(a)).getTime(),
    );

  const centerLabel = (value: string) =>
    value === NO_CENTER ? t.noCenterOption : value;

  if (visibleCommitments.length === 0) {
    return <p className="text-sm text-muted">{t.commitmentsEmpty}</p>;
  }

  const showCenterFilter = centerOptions.length > 0;
  // The viewer's own commitments are only knowable when they are logged in.
  const showMineFilter = currentUsername !== null;

  const filterControls = (showCenterFilter || showMineFilter) && (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
      {showCenterFilter && (
        <div className="w-full sm:w-64">
          <Select
            aria-label={t.filterByCenter}
            selectionMode="multiple"
            value={selectValue}
            onChange={onCenterChange}
          >
            <Select.Trigger>
              <Select.Value>
                {() => {
                  if (centerFilter.length === 0) {
                    return t.allCenters;
                  }
                  // Several joined names overflow the control, so past the first
                  // one collapse to a count.
                  return centerFilter.length === 1 ? (
                    centerLabel(centerFilter[0])
                  ) : (
                    <>
                      {centerFilter.length} {t.centersSelected}
                    </>
                  );
                }}
              </Select.Value>
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox selectionMode="multiple">
                <ListBox.Item
                  key={ALL_CENTERS}
                  id={ALL_CENTERS}
                  textValue={t.allCenters}
                >
                  {t.allCenters}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                {centerOptions.map((name) => (
                  <ListBox.Item key={name} id={name} textValue={name}>
                    {name}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
                {hasUnassigned && (
                  <ListBox.Item
                    key={NO_CENTER}
                    id={NO_CENTER}
                    textValue={t.noCenterOption}
                  >
                    {t.noCenterOption}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                )}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
      )}
      {showMineFilter && (
        <Checkbox isSelected={onlyMine} onChange={setOnlyMine} className="py-1">
          <Checkbox.Content>
            <Checkbox.Control>
              <Checkbox.Indicator />
            </Checkbox.Control>
            <span className="text-sm">{t.onlyMine}</span>
          </Checkbox.Content>
        </Checkbox>
      )}
    </div>
  );

  if (filteredCommitments.length === 0) {
    return (
      <div className="flex flex-col gap-3">
        {filterControls}
        <p className="text-sm text-muted">{t.commitmentsNoMatch}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {filterControls}
      <ul className="flex flex-col gap-2">
        {filteredCommitments.map((c) => {
          // The maker can still resize their own commitment until the units are
          // handed over, so point them at it in "Mis aportes" (FR-057).
          const isMine =
            currentUsername !== null && c.maker_username === currentUsername;
          const canEdit =
            isMine && (c.status === "claimed" || c.status === "prepared");
          return (
            <li
              key={c.id}
              className="flex flex-col gap-2 rounded-lg border px-3 py-2"
              style={{ borderColor: "var(--card-border)" }}
            >
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                <div className="flex min-w-0 items-center gap-3">
                  <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
                    {c.maker_username.slice(0, 1)}
                  </div>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {c.maker_username}
                    </p>
                    {c.collection_center_name && (
                      <p className="truncate text-xs text-muted">
                        {c.collection_center_name}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 flex-col items-start gap-1 pl-10 sm:items-end sm:pl-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm">
                      <strong>{c.quantity}</strong> {t.commitmentUnit}
                    </span>
                    <Chip
                      variant="soft"
                      size="sm"
                      color={STATUS_COLOR[c.status]}
                    >
                      {t.commitmentStatus[c.status]}
                    </Chip>
                  </div>
                  <p className="text-xs text-muted">
                    {t.commitmentStatusDate[c.status]}{" "}
                    {formatStatusDate(statusDate(c), locale)}
                  </p>
                </div>
              </div>
              {canEdit && (
                <p className="text-xs text-muted">
                  {t.editCommitmentPrompt}{" "}
                  <Link
                    href={`/my-contributions#contribution-${c.id}`}
                    className="font-medium text-[var(--accent-strong)] hover:underline"
                  >
                    {t.editCommitmentLink}
                  </Link>
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
