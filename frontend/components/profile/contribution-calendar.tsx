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
  const weekdayLabels = [1, 3, 5].map((index) => ({
    index,
    label: weekdayFormat.format(new Date(start.getTime() + index * DAY_MS)),
  }));

  return (
    <div className="rounded-lg border border-border p-4">
      {/* Horizontal scroll on narrow screens rather than squashing squares. */}
      <div className="overflow-x-auto">
        <div className="inline-flex min-w-max flex-col gap-1">
          <div className="flex gap-[3px] pl-8">
            {monthLabels.map((label, index) => (
              <span
                key={`${label}-${index}`}
                className="w-[11px] text-[10px] text-muted"
              >
                {label}
              </span>
            ))}
          </div>

          <div className="flex gap-[3px]">
            {/* Day-of-week gutter */}
            <div className="relative mr-1 w-7 shrink-0">
              {weekdayLabels.map(({ index, label }) => (
                <span
                  key={label}
                  className="absolute text-[10px] capitalize text-muted"
                  style={{ top: `${index * 14}px` }}
                >
                  {label}
                </span>
              ))}
            </div>

            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="flex flex-col gap-[3px]">
                {week.map((day, dayIndex) => {
                  if (!day) {
                    return <span key={dayIndex} className="size-[11px]" />;
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
                      className={`size-[11px] rounded-[2px] ${LEVEL_CLASS[levelFor(count, busiest)]}`}
                    />
                  );
                })}
              </div>
            ))}
          </div>
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
