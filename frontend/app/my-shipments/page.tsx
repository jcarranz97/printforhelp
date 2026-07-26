import { Card, Chip } from "@heroui/react";
import type { Metadata } from "next";
import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { NewShipmentPanel } from "@/components/shipments/new-shipment-panel";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listMyCollectionCenters } from "@/lib/collection-centers.api";
import { type MyShipment, listMyShipments } from "@/lib/shipments.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.myShipments.title} · PrintForHelp` };
}

const STATUS_COLOR = {
  receiving: "success",
  in_transit: "warning",
  arrived: "success",
  closed: "default",
  cancelled: "danger",
} as const;

function formatDate(iso: string, locale: string): string {
  const dt = new Date(`${iso}T12:00:00`);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleDateString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/**
 * The caller's working queue: every box at every centre they staff.
 *
 * Grouped by centre because that is how the work is organised, and scoped by
 * roster rather than by who pressed create — a contributor helping run a
 * centre sees the same boxes its owner does.
 *
 * Cards mirror the centres directory (whole card is the link, chips above the
 * title) so the page sits in the same visual family as the rest of the site.
 */
export default async function MyShipmentsPage() {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  const { dict, locale } = await getServerI18n();
  const t = dict.myShipments;

  const [shipments, centers] = await Promise.all([
    token ? listMyShipments(token) : Promise.resolve([] as MyShipment[]),
    token ? listMyCollectionCenters(token) : Promise.resolve([]),
  ]);

  const byCenter = new Map<string, MyShipment[]>();
  for (const shipment of shipments) {
    const key = shipment.collection_center_id;
    byCenter.set(key, [...(byCenter.get(key) ?? []), shipment]);
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{t.title}</h1>
          <p className="mt-1 text-sm text-muted">{t.subtitle}</p>
        </div>
      </div>

      {/* Its own block rather than a header action: opening it expands an
          inline form, which would blow the header row apart. */}
      <NewShipmentPanel
        centers={centers.map((c) => ({ id: c.id, name: c.name, city: c.city }))}
      />

      {shipments.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">
              {centers.length === 0 ? t.emptyNoCenters : t.empty}
            </p>
          </Card.Content>
        </Card>
      ) : (
        <div className="flex flex-col gap-10">
          {[...byCenter.entries()].map(([centerId, rows]) => (
            <section key={centerId} className="flex flex-col gap-4">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <h2 className="text-lg font-semibold">
                  {rows[0].collection_center_name}
                </h2>
                <Link
                  href={`/centers/${centerId}`}
                  className="text-sm text-muted underline hover:text-foreground"
                >
                  {t.viewCenter}
                </Link>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {rows.map((shipment) => (
                  <Link
                    key={shipment.id}
                    href={`/centers/${centerId}/shipments/${shipment.id}`}
                    className="rounded-2xl transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2"
                    aria-label={`${t.openBox} ${shipment.shipment_date}`}
                  >
                    <Card className="h-full">
                      <Card.Header>
                        <div className="mb-1 flex flex-wrap gap-1">
                          <Chip
                            size="sm"
                            variant="soft"
                            color={STATUS_COLOR[shipment.status]}
                          >
                            {dict.shipments.status[shipment.status]}
                          </Chip>
                        </div>
                        <Card.Title>
                          {shipment.destination_collection_center_name ??
                            shipment.destination ??
                            t.noDestination}
                        </Card.Title>
                        <Card.Description>
                          {formatDate(shipment.shipment_date, locale)}
                        </Card.Description>
                      </Card.Header>
                      <Card.Content className="flex flex-col gap-1 text-sm">
                        <span className="text-muted">
                          {t.packageCount.replace(
                            "{count}",
                            String(shipment.package_count),
                          )}
                        </span>
                      </Card.Content>
                    </Card>
                  </Link>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
