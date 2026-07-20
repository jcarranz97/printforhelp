"use client";

import { Button } from "@heroui/react";
import Link from "next/link";
import { Fragment, type ReactNode, useState, useTransition } from "react";
import { FiBox, FiEdit3, FiPrinter, FiUserPlus } from "react-icons/fi";

import {
  loadMoreActivityAction,
  setRenameHiddenAction,
} from "@/actions/activity.action";
import { useI18n } from "@/i18n/provider";
import type { Dictionary } from "@/i18n/dictionaries/es";
import type {
  ProfileActivityEntry,
  ProfileActivityKind,
  ProfileActivityMonth,
  ProfileActivityPage,
} from "@/lib/users.api";

const KIND_ICON: Record<ProfileActivityKind, typeof FiPrinter> = {
  claimed: FiUserPlus,
  prepared: FiPrinter,
  delivered: FiBox,
  renamed: FiEdit3,
};

/** Fill `{name}` placeholders in a dictionary string. */
function fill(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

/**
 * Like {@link fill}, but the substituted values are React nodes so they can be
 * styled. Splitting on the placeholders keeps the sentence in the dictionary —
 * translators still control the word order around the highlighted parts.
 */
function fillNodes(
  template: string,
  values: Record<string, ReactNode>,
): ReactNode[] {
  return template.split(/(\{\w+\})/g).map((part, index) => {
    const key = /^\{(\w+)\}$/.exec(part)?.[1];
    return key && key in values ? (
      <Fragment key={index}>{values[key]}</Fragment>
    ) : (
      part
    );
  });
}

/** A handle mentioned in a rename. Deliberately *not* link-styled: the old
 * name no longer resolves, so it must not look clickable. */
function Handle({ children }: { children: ReactNode }) {
  return <strong className="font-semibold text-foreground">{children}</strong>;
}

function formatDay(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    month: "short",
    day: "numeric",
  }).format(date);
}

function monthName(year: number, month: number, locale: string): string {
  // Built as a *local* date on purpose: `Date.UTC` would land on the previous
  // month for viewers behind UTC (July 1st 00:00 UTC is still June 30th in
  // Caracas), labelling the whole group with the wrong month.
  return new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    month: "long",
  }).format(new Date(year, month - 1, 1));
}

type ActivityTimelineProps = {
  username: string;
  initialPage: ProfileActivityPage;
  /** Keeps paging inside the year the profile is filtered to, if any. */
  year: number | null;
  /** Maintainer/admin: can hide/reveal renames (and sees hidden ones). */
  canModerate: boolean;
};

/**
 * The contribution timeline, loaded a couple of months at a time.
 *
 * The profile only ships the newest months; "Show more activity" fetches older
 * ones on demand, so a maker with years of history costs the same first paint
 * as a new one. Pages are keyed by a timestamp cursor, so a month is never
 * split and newly-added activity cannot shift the boundaries mid-read.
 */
export function ActivityTimeline({
  username,
  initialPage,
  year,
  canModerate,
}: ActivityTimelineProps) {
  const { dict, locale } = useI18n();
  const t = dict.profile;

  // Accumulates pages as the reader clicks "Show more". The parent remounts
  // this component (keyed on the year) when the filter changes, so this state
  // always belongs to the year currently on screen.
  const [months, setMonths] = useState(initialPage.months);
  const [cursor, setCursor] = useState(initialPage.next_before);
  const [hasMore, setHasMore] = useState(initialPage.has_more);
  const [failed, setFailed] = useState(false);
  const [isLoading, startLoading] = useTransition();

  // Flip a rename's hidden flag in place after a moderator toggles it. The
  // moderator keeps seeing the entry (greyed out); only its badge/label change.
  function applyRenameHidden(changeId: string, hidden: boolean) {
    setMonths((current) =>
      current.map((month) => ({
        ...month,
        entries: month.entries.map((entry) =>
          entry.rename_id === changeId
            ? { ...entry, rename_hidden: hidden }
            : entry,
        ),
      })),
    );
  }

  function loadMore() {
    if (!cursor) {
      return;
    }
    setFailed(false);
    startLoading(async () => {
      const page = await loadMoreActivityAction(username, cursor, year);
      if (!page) {
        setFailed(true);
        return;
      }
      setMonths((current) => [...current, ...page.months]);
      setCursor(page.next_before);
      setHasMore(page.has_more);
    });
  }

  if (months.length === 0) {
    return (
      <p className="rounded-lg border border-border py-10 text-center text-sm text-muted">
        {t.emptyActivity}
      </p>
    );
  }

  return (
    <div className="flex flex-col">
      {months.map((month) => (
        <div key={`${month.year}-${month.month}`} className="flex flex-col">
          <div className="mb-1 flex items-center gap-3">
            <span className="whitespace-nowrap text-sm">
              <strong className="font-bold capitalize">
                {monthName(month.year, month.month, locale)}
              </strong>{" "}
              <span className="text-muted">{month.year}</span>
            </span>
            <span className="h-px flex-1 bg-border" />
            {/* Deduplicated: the stage lines below overlap, this does not. */}
            {/* A month may hold only profile events (e.g. a rename), and
                "0 contributions" would read as a bug rather than a fact. */}
            {month.contributions_count > 0 ? (
              <span className="whitespace-nowrap text-xs text-muted">
                {fill(
                  month.contributions_count === 1
                    ? t.monthContributionsOne
                    : t.monthContributions,
                  { count: month.contributions_count },
                )}
              </span>
            ) : null}
          </div>

          {month.entries.map((entry) => (
            <TimelineEntry
              key={`${entry.kind}-${entry.occurred_at}`}
              entry={entry}
              dict={dict}
              locale={locale}
              canModerate={canModerate}
              onToggleHidden={applyRenameHidden}
            />
          ))}
        </div>
      ))}

      {hasMore ? (
        <div className="mt-2 flex flex-col items-center gap-2">
          <Button
            variant="secondary"
            fullWidth
            onPress={loadMore}
            isPending={isLoading}
          >
            {isLoading ? t.loadingActivity : t.showMoreActivity}
          </Button>
          {failed ? (
            <span className="text-xs text-danger">{t.activityLoadError}</span>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function TimelineEntry({
  entry,
  dict,
  locale,
  canModerate,
  onToggleHidden,
}: {
  entry: ProfileActivityEntry;
  dict: Dictionary;
  locale: string;
  canModerate: boolean;
  onToggleHidden: (changeId: string, hidden: boolean) => void;
}) {
  const t = dict.profile;
  const Icon = KIND_ICON[entry.kind];
  const unit = entry.unit?.trim() || t.unitsPieces;
  const summary =
    entry.kind === "renamed"
      ? fillNodes(t.activityRenamed, {
          from: <Handle>{entry.renamed_from}</Handle>,
          to: <Handle>{entry.renamed_to}</Handle>,
        })
      : summaryFor(entry, unit, t);
  // Scaled within the entry: the bars compare projects *inside* one action.
  // Scaling across the month would pit a claim against a print — different
  // stages of the same units — and squash the smaller stage into dots.
  const scaleTo = Math.max(...entry.items.map((item) => item.quantity), 1);

  // A rename with a change id is only ever sent to a maintainer/admin, so the
  // moderator controls hang off it. Hidden renames are dimmed so it is obvious
  // the public can't see them.
  const [toggling, startToggle] = useTransition();
  const [toggleFailed, setToggleFailed] = useState(false);
  const canToggleRename = canModerate && entry.rename_id !== null;
  const isHidden = entry.rename_hidden;

  function toggleHidden() {
    const changeId = entry.rename_id;
    if (!changeId) {
      return;
    }
    const next = !isHidden;
    setToggleFailed(false);
    startToggle(async () => {
      const ok = await setRenameHiddenAction(changeId, next);
      if (ok) {
        onToggleHidden(changeId, next);
      } else {
        setToggleFailed(true);
      }
    });
  }

  return (
    <div className="flex gap-4 pl-1">
      {/* Rail + icon */}
      <div className="flex w-8 flex-none flex-col items-center">
        <span className="min-h-3 w-px flex-1 bg-border" />
        <span className="flex size-8 items-center justify-center rounded-full border border-border bg-default-100 text-muted">
          <Icon className="size-3.5" aria-hidden />
        </span>
        <span className="min-h-3 w-px flex-1 bg-border" />
      </div>

      {/* Body */}
      <div className={`flex-1 py-2 pb-5 ${isHidden ? "opacity-60" : ""}`}>
        <div className="flex items-start justify-between gap-3">
          <span className="text-sm leading-snug">
            {summary}
            {isHidden ? (
              <span className="ml-2 inline-block whitespace-nowrap rounded-full bg-default-200 px-2 py-0.5 align-middle text-xs font-medium text-muted">
                {t.renameHiddenBadge}
              </span>
            ) : null}
          </span>
          {/* The most recent activity in the group. */}
          <span className="whitespace-nowrap pt-0.5 text-xs text-muted">
            {formatDay(entry.occurred_at, locale)}
          </span>
        </div>

        {canToggleRename ? (
          <div className="mt-2 flex items-center gap-3">
            <Button
              variant="secondary"
              size="sm"
              onPress={toggleHidden}
              isPending={toggling}
            >
              {isHidden ? t.renameShow : t.renameHide}
            </Button>
            {toggleFailed ? (
              <span className="text-xs text-danger">{t.renameHideError}</span>
            ) : null}
          </div>
        ) : null}

        {entry.items.length > 0 ? (
          <div className="mt-3 flex flex-col gap-2">
            {entry.items.map((item) => (
              <div
                key={`${item.request_id}-${item.item_number}`}
                className="grid grid-cols-[1fr_auto] items-center gap-4 sm:grid-cols-[1fr_168px]"
              >
                <span className="min-w-0 truncate text-sm">
                  <Link
                    href={`/requests/${item.request_id}/items/${item.item_number}`}
                    className="font-semibold text-accent hover:underline"
                  >
                    {item.resource_name}
                  </Link>{" "}
                  <span className="ml-1 text-muted">
                    {item.quantity} {item.unit?.trim() || t.unitsPieces}
                  </span>
                </span>
                <span
                  className="h-2 rounded-full bg-success"
                  style={{
                    // Floor at 4% so the smallest contribution is still a
                    // visible mark rather than an empty row.
                    width: `${Math.max(4, Math.round((item.quantity / scaleTo) * 100))}%`,
                  }}
                />
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** Build the one-line summary for a timeline entry. */
function summaryFor(
  entry: ProfileActivityEntry,
  unit: string,
  t: Dictionary["profile"],
): string {
  const vars = {
    total: entry.total_quantity,
    unit,
    count: entry.request_count,
    request: entry.single_request_title ?? "",
  };
  // Each kind has a one-request variant so the summary never reads
  // "1 requests" — and can name the campaign instead of counting it.
  const single = entry.single_request_title !== null;
  const template =
    entry.kind === "delivered"
      ? single
        ? t.activityDeliveredOne
        : t.activityDelivered
      : entry.kind === "prepared"
        ? single
          ? t.activityPrintedOne
          : t.activityPrinted
        : single
          ? t.activityClaimedOne
          : t.activityClaimed;
  return fill(template, vars);
}
