"use client";

import { Card, Chip } from "@heroui/react";
import Link from "next/link";

import { CenterReceivingChip } from "@/components/centers/center-receiving-chip";
import { useI18n } from "@/i18n/provider";
import type { CollectionCenter } from "@/lib/collection-centers.api";

/**
 * One centre in a grid of centres.
 *
 * Shared by the public directory and the caller's own "My centres" list so a
 * centre reads identically wherever it appears — the whole card is the link,
 * status chips sit above the name, and the details stack underneath.
 *
 * The **private** chip only ever shows on "My centres": an unlisted centre is
 * excluded from the public directory by definition, and its owner needs to see
 * at a glance which of theirs are hidden from it.
 */
export function CenterCard({ center }: { center: CollectionCenter }) {
  const { dict } = useI18n();
  const t = dict.centers;
  return (
    <Link
      href={`/centers/${center.id}`}
      className="rounded-2xl transition-shadow hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2"
      aria-label={`${t.viewDetails} ${center.name}`}
    >
      <Card className="h-full">
        <Card.Header>
          <div className="mb-1 flex flex-wrap gap-1">
            <CenterReceivingChip status={center.status} />
            {center.verified ? (
              <Chip color="success" variant="soft" size="sm">
                {t.verified}
              </Chip>
            ) : (
              <Chip color="warning" variant="soft" size="sm">
                {t.unverified}
              </Chip>
            )}
            {!center.listed && (
              <Chip variant="soft" size="sm">
                {dict.myCenters.unlisted}
              </Chip>
            )}
          </div>
          <Card.Title>{center.name}</Card.Title>
          <Card.Description>
            {[center.city, center.state, center.country]
              .filter(Boolean)
              .join(", ")}
          </Card.Description>
        </Card.Header>
        <Card.Content className="flex flex-col gap-1 text-sm">
          <span className="text-muted">{center.address}</span>
          <span className="font-medium">{center.contact}</span>
          {center.opening_hours && (
            <span className="text-muted">{center.opening_hours}</span>
          )}
          {center.tags.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {center.tags.map((tag) => (
                <Chip key={tag} variant="soft" size="sm">
                  {tag}
                </Chip>
              ))}
            </div>
          )}
        </Card.Content>
      </Card>
    </Link>
  );
}
