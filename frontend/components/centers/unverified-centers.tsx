import { Card, Chip } from "@heroui/react";

import { getServerI18n } from "@/i18n/server";
import type { CollectionCenter } from "@/lib/collection-centers.api";

import { CenterVerifyButton } from "./center-verify-button";

/**
 * The maintainer review queue: every center that is not yet verified, each
 * with a one-click verify control. "Unverified" is simply `verified=false`
 * — there is no separate state. These centers are already public (badged
 * "No verificado" in the main directory); this is just a focused work list.
 */
export async function UnverifiedCenters({
  centers,
}: {
  centers: CollectionCenter[];
}) {
  const { dict } = await getServerI18n();
  const t = dict.centers;

  return (
    <section className="mt-12">
      <h2 className="text-lg font-semibold">{t.queueHeading}</h2>
      <p className="mt-1 mb-4 text-sm text-muted">{t.queueDescription}</p>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {centers.map((center) => (
          <Card key={center.id} className="h-full">
            <Card.Header>
              <Card.Title>{center.name}</Card.Title>
              <Card.Description>
                {center.city}, {center.country}
              </Card.Description>
            </Card.Header>
            <Card.Content className="flex flex-col gap-1 text-sm">
              <span className="text-muted">{center.address}</span>
              <span className="font-medium">{center.contact}</span>
            </Card.Content>
            <Card.Footer className="flex flex-wrap items-center justify-between gap-2">
              <Chip color="warning" variant="soft" size="sm">
                {t.unverified}
              </Chip>
              <CenterVerifyButton centerId={center.id} verified={false} />
            </Card.Footer>
          </Card>
        ))}
      </div>
    </section>
  );
}
