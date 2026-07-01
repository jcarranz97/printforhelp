import type { PartStats } from "@/lib/parts.api";

/**
 * Localized labels for {@link RequestClaimBar}. Passed in as props rather
 * than read from a hook so the same component works in both server
 * components (the part detail page) and client components (the catalog).
 */
export type RequestClaimBarLabels = {
  heading: string;
  subtitle: string;
  requests: string;
  claims: string;
  requestsHint: string;
  claimsHint: string;
  needsMakers: string;
  covered: string;
  noActivity: string;
  ariaLabel: string;
};

// Demand (people still asking) reads as warm; supply (makers printing)
// reads as green. Fixed hex keeps the meaning identical in light/dark.
const REQUEST_COLOR = "#f59e0b";
const CLAIM_COLOR = "#10b981";

function pct(part: number, total: number): number {
  return total === 0 ? 0 : Math.round((part / total) * 100);
}

/**
 * A two-segment bar comparing open requests against active maker claims
 * for a single Part. ``compact`` renders just the bar + counts for catalog
 * cards; the full variant adds a heading, legend, and a plain-language
 * status line for the detail page.
 */
export function RequestClaimBar({
  stats,
  labels,
  compact = false,
}: {
  stats: PartStats;
  labels: RequestClaimBarLabels;
  compact?: boolean;
}) {
  const requests = stats.request_count;
  const claims = stats.claim_count;
  const total = requests + claims;
  const requestPct = pct(requests, total);
  const claimPct = total === 0 ? 0 : 100 - requestPct;
  const ariaValue =
    total === 0 ? labels.noActivity : `${requests} / ${claims}`;

  const bar = (
    <div
      className="flex h-2.5 w-full overflow-hidden rounded-full"
      style={{ background: "color-mix(in srgb, var(--foreground) 10%, transparent)" }}
      role="img"
      aria-label={`${labels.ariaLabel}: ${ariaValue}`}
    >
      {requests > 0 && (
        <div style={{ width: `${requestPct}%`, background: REQUEST_COLOR }} />
      )}
      {claims > 0 && (
        <div style={{ width: `${claimPct}%`, background: CLAIM_COLOR }} />
      )}
    </div>
  );

  if (compact) {
    return (
      <div className="flex flex-col gap-1.5">
        {bar}
        <div
          className="flex justify-between text-xs"
          style={{ color: "var(--muted)" }}
        >
          <span>
            <Dot color={REQUEST_COLOR} /> {requests} {labels.requests}
          </span>
          <span>
            <Dot color={CLAIM_COLOR} /> {claims} {labels.claims}
          </span>
        </div>
      </div>
    );
  }

  const needsMakers = requests > claims;
  return (
    <section
      className="rounded-2xl border p-5"
      style={{ background: "var(--card)", borderColor: "var(--card-border)" }}
      aria-label={labels.ariaLabel}
    >
      <h2 className="text-lg font-semibold">{labels.heading}</h2>
      <p className="mt-1 text-sm" style={{ color: "var(--muted)" }}>
        {labels.subtitle}
      </p>

      <div className="mt-4">{bar}</div>

      <dl className="mt-4 grid grid-cols-2 gap-4">
        <Stat
          color={REQUEST_COLOR}
          value={requests}
          label={labels.requests}
          hint={labels.requestsHint}
        />
        <Stat
          color={CLAIM_COLOR}
          value={claims}
          label={labels.claims}
          hint={labels.claimsHint}
        />
      </dl>

      <p className="mt-4 text-sm font-medium">
        {total === 0
          ? labels.noActivity
          : needsMakers
            ? labels.needsMakers
            : labels.covered}
      </p>
    </section>
  );
}

function Dot({ color }: { color: string }) {
  return (
    <span
      aria-hidden
      className="mr-1 inline-block h-2 w-2 rounded-full align-middle"
      style={{ background: color }}
    />
  );
}

function Stat({
  color,
  value,
  label,
  hint,
}: {
  color: string;
  value: number;
  label: string;
  hint: string;
}) {
  return (
    <div>
      <dt className="flex items-center gap-2 text-sm font-medium">
        <span
          aria-hidden
          className="inline-block h-2.5 w-2.5 rounded-full"
          style={{ background: color }}
        />
        {label}
      </dt>
      <dd className="mt-1">
        <span className="text-2xl font-bold">{value}</span>
        <span className="ml-2 text-xs" style={{ color: "var(--muted)" }}>
          {hint}
        </span>
      </dd>
    </div>
  );
}
