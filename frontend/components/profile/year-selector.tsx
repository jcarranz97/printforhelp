import Link from "next/link";

import type { Dictionary } from "@/i18n/dictionaries/es";

type YearSelectorProps = {
  username: string;
  years: number[];
  selected: number | null;
  dict: Dictionary;
};

/**
 * Year filter beside the contribution calendar.
 *
 * Plain links rather than client state: switching year re-renders the profile
 * on the server (calendar, headline and timeline all scope to it), and the
 * choice lives in the URL so it can be shared and navigated back through.
 */
export function YearSelector({
  username,
  years,
  selected,
  dict,
}: YearSelectorProps) {
  const t = dict.profile;
  const base = "rounded-md px-3 py-1.5 text-left text-sm transition-colors";
  const active = `${base} bg-accent text-accent-foreground font-semibold`;
  const idle = `${base} text-muted hover:bg-default-100 hover:text-foreground`;

  return (
    <nav
      aria-label={t.yearFilterLabel}
      className="flex shrink-0 flex-row gap-1 overflow-x-auto md:w-24 md:flex-col md:overflow-visible"
    >
      <Link href={`/${username}`} className={selected === null ? active : idle}>
        {t.yearAll}
      </Link>
      {years.map((year) => (
        <Link
          key={year}
          href={`/${username}?year=${year}`}
          className={selected === year ? active : idle}
        >
          {year}
        </Link>
      ))}
    </nav>
  );
}
