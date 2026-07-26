import { Card, Chip } from "@heroui/react";
import Link from "next/link";

import { ShipmentContentsList } from "@/components/shipments/shipment-contents-list";
import type { Dictionary } from "@/i18n/dictionaries";
import type { ShipmentTrackingSummary } from "@/lib/tracking.api";

/**
 * What a scanned box shows: where it is going, how much it carries, and the
 * chain of bigger boxes it currently rides in.
 *
 * Includes the manifest, so the centre expecting this box can see what is
 * coming — how many contributions, of what, from whom. The backend has already
 * redacted every line the viewer may not read (FR-146): a box is public while
 * the packages inside it need not be, so a passer-by scanning the label sees
 * counts and placeholders where staff see the itemised list.
 */
export function BoxSummary({
  summary,
  t,
  statusLabels,
}: {
  summary: ShipmentTrackingSummary;
  t: Dictionary["shipments"];
  statusLabels: Dictionary["shipments"]["status"];
}) {
  const status =
    statusLabels[summary.status as keyof typeof statusLabels] ?? summary.status;
  return (
    <Card>
      <Card.Content className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">📦 → {summary.destination}</h1>
          <Chip variant="soft" size="sm">
            {status}
          </Chip>
        </div>

        <p className="text-sm text-muted">
          {t.contentsSummary
            .replace("{packages}", String(summary.package_count))
            .replace("{units}", String(summary.units_total))}
          {summary.child_count > 0 &&
            ` · ${t.contentsNested.replace(
              "{count}",
              String(summary.child_count),
            )}`}
        </p>
        {summary.hidden_count > 0 && (
          <p className="text-sm text-muted">
            {t.contentsHidden.replace("{count}", String(summary.hidden_count))}
          </p>
        )}

        {/* What is actually inside. Redacted server-side for anyone who is
            not centre staff, so this is safe to render unconditionally. */}
        {summary.entries.length > 0 && (
          <div className="flex flex-col gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              {t.boxTitle}
            </span>
            <ShipmentContentsList entries={summary.entries} />
          </div>
        )}

        {summary.route.length > 0 && (
          <div className="flex flex-col gap-1">
            <span className="text-xs font-medium uppercase tracking-wide text-muted">
              {t.routeTitle}
            </span>
            <span className="text-sm">
              {t.routeInside}{" "}
              {summary.route.map((hop, index) => (
                <span key={hop.shipment_id}>
                  {index > 0 && " → "}
                  <Link
                    href={`/track/${hop.tracking_token}`}
                    className="underline"
                  >
                    {hop.label}
                  </Link>
                </span>
              ))}
            </span>
          </div>
        )}
      </Card.Content>
    </Card>
  );
}
