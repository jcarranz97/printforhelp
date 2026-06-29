import { Card, Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";
import { FaMapMarkerAlt } from "react-icons/fa";

import { getCurrentUser } from "@/actions/auth.action";
import { CenterArchiveButton } from "@/components/centers/center-archive-button";
import { CenterVerifyButton } from "@/components/centers/center-verify-button";
import { EntityFeed } from "@/components/comments/entity-feed";
import { ShipmentsPanel } from "@/components/shipments/shipments-panel";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import {
  type CollectionCenter,
  canManageCenter,
  getCollectionCenter,
} from "@/lib/collection-centers.api";
import { listActivity, listComments } from "@/lib/feed.api";
import { type Organization, getOrganization } from "@/lib/organizations.api";
import { listShipments } from "@/lib/shipments.api";

type DetailRowProps = {
  label: string;
  children: React.ReactNode;
};

function DetailRow({ label, children }: DetailRowProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs font-medium uppercase tracking-wide text-muted">
        {label}
      </span>
      <span className="text-sm">{children}</span>
    </div>
  );
}

/**
 * Render the owning-principal section. An org-owned center shows the org
 * name when the org is publicly visible (verified); when the org is hidden
 * (unverified, FR-105) it shows an "unverified organization" badge instead.
 */
function OwnerSection({
  center,
  organization,
  t,
}: {
  center: CollectionCenter;
  organization: Organization | null;
  t: Dictionary["centerDetail"];
}) {
  if (center.owner_organization_id) {
    if (organization) {
      return (
        <DetailRow label={t.organization}>
          <span className="inline-flex items-center gap-2">
            {organization.name}
            <Chip color="success" variant="soft" size="sm">
              {t.orgVerified}
            </Chip>
          </span>
        </DetailRow>
      );
    }
    return (
      <DetailRow label={t.organization}>
        <Chip color="warning" variant="soft" size="sm">
          {t.orgUnverified}
        </Chip>
      </DetailRow>
    );
  }

  return <DetailRow label={t.management}>{t.managedIndividually}</DetailRow>;
}

export default async function CenterDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const user = await getCurrentUser();
  const token = user
    ? (await cookies()).get(AUTH_COOKIE_NAME)?.value
    : undefined;
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const { dict } = await getServerI18n();
  const t = dict.centerDetail;

  const center = await getCollectionCenter(id, token);
  if (!center) {
    notFound();
  }

  const organization = center.owner_organization_id
    ? await getOrganization(center.owner_organization_id)
    : null;

  const viewer = user ? { id: user.id, role: user.role } : null;
  const [shipments, canManage, centerComments, centerActivity] =
    await Promise.all([
      listShipments(center.id),
      canManageCenter(center.id, token),
      listComments("collection_center", center.id),
      listActivity("collection_center", center.id),
    ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link
        href="/centers"
        className="text-sm text-muted hover:text-foreground"
      >
        {t.back}
      </Link>

      <div className="mt-4 mb-8 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold">{center.name}</h1>
          {center.verified ? (
            <Chip color="success" variant="soft" size="sm">
              {t.verified}
            </Chip>
          ) : (
            <Chip color="warning" variant="soft" size="sm">
              {t.unverified}
            </Chip>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {user && (
            <Link
              href={`/centers/new?cloneFrom=${center.id}`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.clone}
            </Link>
          )}
          {canManage && (
            <Link
              href={`/centers/${center.id}/edit`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.edit}
            </Link>
          )}
          {isMaintainer && (
            <CenterVerifyButton
              centerId={center.id}
              verified={center.verified}
            />
          )}
          {canManage && center.active && (
            <CenterArchiveButton
              centerId={center.id}
              isMaintainer={isMaintainer}
            />
          )}
        </div>
      </div>

      <Card>
        <Card.Content className="grid gap-5 sm:grid-cols-2">
          <DetailRow label={t.address}>
            <span className="flex flex-col gap-1">
              <span>{center.address}</span>
              {center.location_url ? (
                <a
                  href={center.location_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex w-fit items-center gap-1 font-medium underline"
                  style={{ color: "var(--accent-strong)" }}
                >
                  <FaMapMarkerAlt aria-hidden className="h-3.5 w-3.5" />
                  {t.viewOnMap}
                </a>
              ) : (
                <span
                  className="inline-flex w-fit items-center gap-1 text-xs text-muted"
                  title={t.noMapLinkHint}
                >
                  <FaMapMarkerAlt aria-hidden className="h-3.5 w-3.5" />
                  {t.noMapLink}
                </span>
              )}
            </span>
          </DetailRow>
          <DetailRow label={t.city}>
            {center.city}, {center.country}
          </DetailRow>
          <DetailRow label={t.contact}>{center.contact}</DetailRow>
          {center.opening_hours && (
            <DetailRow label={t.hours}>{center.opening_hours}</DetailRow>
          )}
          <OwnerSection center={center} organization={organization} t={t} />
          {center.notes && (
            <div className="sm:col-span-2">
              <DetailRow label={t.notes}>{center.notes}</DetailRow>
            </div>
          )}
        </Card.Content>
      </Card>

      <ShipmentsPanel
        centerId={center.id}
        shipments={shipments}
        canManage={canManage}
      />

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/centers/${center.id}`}
          entityType="collection_center"
          entityId={center.id}
          comments={centerComments}
          activity={centerActivity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
