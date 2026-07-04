import { countryFlag, countryName } from "@/lib/country";

/**
 * Countries badge: a floating pill with one flag circle per country (stacked)
 * and the label beside them. A single country reads "Only {country}"; several
 * are listed by name. Reused by the campaign cards (directory) and the per-item
 * cards (request detail).
 */
export function CountryBadge({
  codes,
  onlyLabel,
  locale,
}: {
  codes: string[];
  onlyLabel: string;
  locale: string;
}) {
  const names = codes.map((code) => countryName(code, locale));
  const label =
    codes.length === 1 ? `${onlyLabel} ${names[0]}` : names.join(", ");
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-background py-1 pl-1 pr-3 text-xs font-medium text-foreground shadow-md ring-1 ring-default-200">
      <span aria-hidden className="flex items-center -space-x-1.5">
        {codes.map((code) => (
          <span
            key={code}
            className="flex h-6 w-6 items-center justify-center rounded-full bg-white text-base leading-none ring-1 ring-default-200"
          >
            {countryFlag(code) ?? "🌍"}
          </span>
        ))}
      </span>
      {label}
    </span>
  );
}
