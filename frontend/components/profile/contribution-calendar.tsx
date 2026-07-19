import { Fragment } from "react";

import type { Dictionary } from "@/i18n/dictionaries/es";
import type { ProfileContributionDay } from "@/lib/users.api";

const DAY_MS = 86_400_000;
/**
 * Intensity buckets: empty plus four shades (GitHub uses the same count).
 *
 * The empty square is a tint of the foreground rather than a `default-*`
 * shade, which sits too close to the surface colour to be visible — the grid
 * has to read as a grid on quiet days, not as scattered dots.
 */
const LEVEL_CLASS = [
  "bg-[color-mix(in_srgb,var(--foreground)_9%,transparent)]",
  "bg-success/30",
  "bg-success/55",
  "bg-success/80",
  "bg-success",
];

/**
 * All dates are handled in UTC — the API sends plain `YYYY-MM-DD` days, and
 * parsing those as local time would shift every square (and the month labels)
 * back a day for anyone behind UTC.
 */
function utcDay(date: Date): string {
  return date.toISOString().slice(0, 10);
}

/** Bucket a day's count into 0-4, scaled to the busiest day of the year. */
function levelFor(count: number, busiest: number): number {
  if (count <= 0) {
    return 0;
  }
  return Math.min(4, Math.ceil((count / busiest) * 4));
}

function fill(
  template: string,
  values: Record<string, string | number>,
): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in values ? String(values[key]) : match,
  );
}

type ContributionCalendarProps = {
  days: ProfileContributionDay[];
  /** The calendar year shown, or null for a rolling last-12-months grid. */
  year: number | null;
  dict: Dictionary;
  locale: string;
};

/**
 * A year of contribution activity as a heat map: one column per week, one
 * square per day, shaded by how many commitments were active that day.
 *
 * The API sends only days that have activity, so the empty squares are filled
 * in here rather than shipping 365 zeroes.
 */
export function ContributionCalendar({
  days,
  year,
  dict,
  locale,
}: ContributionCalendarProps) {
  const t = dict.profile;
  const counts = new Map(days.map((day) => [day.date, day.count]));
  const busiest = Math.max(...days.map((day) => day.count), 1);

  const now = new Date();
  const today = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );
  // A selected year spans that whole calendar year, so the grid lines up with
  // the year label; the default view is a rolling 12 months ending today.
  const end = year === null ? today : new Date(Date.UTC(year, 11, 31));
  const firstDay =
    year === null
      ? new Date(end.getTime() - 364 * DAY_MS)
      : new Date(Date.UTC(year, 0, 1));
  // Rewind to that week's Sunday so every column is a full week and the
  // day-of-week rows line up.
  const start = new Date(firstDay.getTime() - firstDay.getUTCDay() * DAY_MS);

  const weeks: (string | null)[][] = [];
  for (
    let cursor = start;
    cursor <= end;
    cursor = new Date(cursor.getTime() + 7 * DAY_MS)
  ) {
    weeks.push(
      Array.from({ length: 7 }, (_, offset) => {
        const day = new Date(cursor.getTime() + offset * DAY_MS);
        // Days outside the window — and days still in the future when the
        // current year is selected — leave a gap rather than an empty square.
        return day > end || day > today || day < firstDay ? null : utcDay(day);
      }),
    );
  }

  const monthFormat = new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    month: "short",
    timeZone: "UTC",
  });
  const dateFormat = new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    dateStyle: "long",
    timeZone: "UTC",
  });
  const weekdayFormat = new Intl.DateTimeFormat(locale === "es" ? "es" : "en", {
    weekday: "short",
    timeZone: "UTC",
  });

  // A label sits above the first column of each new month. Tracked against the
  // last month actually labelled rather than the previous column's first cell,
  // which is empty at a year boundary and would repeat the label.
  let labelledMonth = -1;
  const monthLabels = weeks.map((week) => {
    const first = week.find(Boolean);
    if (!first) {
      return null;
    }
    const day = new Date(`${first}T00:00:00Z`);
    if (day.getUTCMonth() === labelledMonth) {
      return null;
    }
    labelledMonth = day.getUTCMonth();
    return monthFormat.format(day);
  });

  // Mon/Wed/Fri only, like GitHub — labelling all seven is unreadable.
  const weekdayLabels = Array.from({ length: 7 }, (_, index) =>
    index === 1 || index === 3 || index === 5
      ? weekdayFormat.format(new Date(start.getTime() + index * DAY_MS))
      : "",
  );

  return (
    <div className="rounded-lg border border-border p-4">
      {/* Scrolls only once the squares would get too small to read; on a normal
          screen the whole year fits, because the columns are fractions of the
          available width rather than a fixed 11px. */}
      <div className="overflow-x-auto">
        <div
          className="grid min-w-[420px] gap-[2px] text-[10px]"
          style={{
            // A fixed gutter for the weekday labels (they are positioned
            // absolutely, so they cannot size it), then one equal fraction per
            // week. `minmax(0, …)` lets the weeks shrink below their content.
            gridTemplateColumns: `28px repeat(${weeks.length}, minmax(0, 1fr))`,
            // Stop growing at GitHub's square size (11px + the 2px gap) so a
            // wide viewport gets a calendar, not a chessboard.
            maxWidth: `${weeks.length * 13 + 32}px`,
          }}
        >
          {/* Header row: an empty corner over the gutter, then month labels.
              These overflow their one-column cell on purpose — "sept" is wider
              than a square, and the next cell is usually blank anyway. */}
          <span />
          {monthLabels.map((label, index) => (
            <span
              key={`${label}-${index}`}
              className="whitespace-nowrap text-muted"
            >
              {label}
            </span>
          ))}

          {/* One row per weekday. Row-major order means the gutter label and
              that day's squares stay aligned however wide the cells get. */}
          {weekdayLabels.map((label, dayIndex) => (
            <Fragment key={dayIndex}>
              {/* The label is absolutely positioned so it contributes no
                  height: 10px text is taller than a square, and letting it
                  size the row would stretch Mon/Wed/Fri and band the grid. */}
              <span className="relative pr-1">
                <span className="absolute right-1 top-1/2 -translate-y-1/2 capitalize leading-none text-muted">
                  {label}
                </span>
              </span>
              {weeks.map((week, weekIndex) => {
                const day = week[dayIndex];
                if (!day) {
                  return <span key={weekIndex} className="aspect-square" />;
                }
                const count = counts.get(day) ?? 0;
                const when = dateFormat.format(new Date(`${day}T00:00:00Z`));
                return (
                  <span
                    key={day}
                    title={fill(
                      count === 0
                        ? t.calendarNone
                        : count === 1
                          ? t.calendarDayOne
                          : t.calendarDay,
                      { count, date: when },
                    )}
                    className={`aspect-square rounded-[2px] ${LEVEL_CLASS[levelFor(count, busiest)]}`}
                  />
                );
              })}
            </Fragment>
          ))}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-1 text-[11px] text-muted">
        <span>{t.calendarLess}</span>
        {LEVEL_CLASS.map((className) => (
          <span
            key={className}
            className={`size-[11px] rounded-[2px] ${className}`}
          />
        ))}
        <span>{t.calendarMore}</span>
      </div>
    </div>
  );
}
