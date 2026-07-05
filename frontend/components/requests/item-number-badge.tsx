/**
 * Small muted pill showing an item's per-request number (e.g. "#2"). Styled
 * as a badge (not plain text) so it reads as an identifier tag rather than
 * part of the Resource name. Pure presentational — safe in server or client
 * components.
 */
export function ItemNumberBadge({
  number,
  className,
}: {
  number: number;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full bg-default-100 px-2.5 py-0.5 text-sm font-medium text-muted ${
        className ?? ""
      }`}
    >
      #{number}
    </span>
  );
}
