import { Card, Chip } from "@heroui/react";

import { getServerI18n } from "@/i18n/server";
import type { CollectionCenter } from "@/lib/collection-centers.api";

import { CenterRestoreButton } from "./center-restore-button";

/**
 * The maintainer recovery queue: every archived (soft-deleted) center, each
 * with a one-click restore control. Archived centers are hidden from the
 * public directory; this focused list lets maintainers review what was
 * removed and bring any of them back.
 */
export async function ArchivedCenters({
  centers,
}: {
  centers: CollectionCenter[];
}) {
  const { dict } = await getServerI18n();
  const t = dict.centers;

  return (
    <section className="mt-12">
      <h2 className="text-lg font-semibold">{t.archivedHeading}</h2>
      <p className="mt-1 mb-4 text-sm text-muted">{t.archivedDescription}</p>

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
              <Chip color="default" variant="soft" size="sm">
                {t.archivedBadge}
              </Chip>
              <CenterRestoreButton centerId={center.id} />
            </Card.Footer>
          </Card>
        ))}
      </div>
    </section>
  );
}
