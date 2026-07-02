import type { Metadata } from "next";
import { Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { EntityFeed } from "@/components/comments/entity-feed";
import { WatchButton } from "@/components/notifications/watch-button";
import { EntityNoticeBanner } from "@/components/notices/entity-notice-banner";
import { RequestNotice } from "@/components/notices/request-notice";
import { getServerI18n } from "@/i18n/server";
import { listActivity, listComments } from "@/lib/feed.api";
import { getSupply } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.supplies.title} · PrintForHelp` };
}

export default async function SupplyDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string; fromReq?: string; fromItem?: string }>;
}) {
  const { id } = await params;
  const { from, fromReq, fromItem } = await searchParams;
  const supply = await getSupply(id);
  if (!supply) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const t = dict.supplyDetail;
  // Contextual back link based on where the visitor came from:
  // - from a request item (`?from=item&fromReq=R&fromItem=N`) → back to it
  // - from My Contributions (`?from=contributions`) → back there
  // - otherwise → the public catalog
  const fromItemNav = from === "item" && !!fromReq && !!fromItem;
  const fromContributions = from === "contributions";
  let backHref = "/supplies";
  let backLabel = t.back;
  if (fromItemNav) {
    backHref = `/requests/${fromReq}/items/${fromItem}`;
    backLabel = `← ${t.backToItem} ${supply.name} #${fromItem}`;
  } else if (fromContributions) {
    backHref = "/my-contributions";
    backLabel = t.backToContributions;
  }
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canEdit = !!user && (user.id === supply.owner_user_id || isMaintainer);

  const viewer = user ? { id: user.id, role: user.role } : null;
  const [comments, activity, watching] = await Promise.all([
    listComments("resource", supply.id),
    listActivity("resource", supply.id),
    user
      ? fetchWatchStateAction("resource", supply.id)
      : Promise.resolve(false),
  ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href={backHref} className="text-sm text-muted hover:underline">
        {backLabel}
      </Link>

      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{supply.name}</h1>
          {supply.status === "discontinued" && (
            <Chip color="warning" variant="soft" size="sm">
              {t.discontinued}
            </Chip>
          )}
        </div>
        <div className="flex items-center gap-2">
          {user && (
            <WatchButton
              entityType="resource"
              entityId={supply.id}
              initialWatching={watching}
            />
          )}
          {canEdit && (
            <Link
              href={`/supplies/${supply.id}/edit`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.edit}
            </Link>
          )}
        </div>
      </div>

      <EntityNoticeBanner targetType="resource" targetId={supply.id} />
      {canEdit && (
        <RequestNotice
          targetType="resource"
          targetId={supply.id}
          revalidate={`/supplies/${supply.id}`}
          isMaintainer={isMaintainer}
        />
      )}

      {supply.image_url && (
        // External, user-supplied image URL — see supplies-catalog.tsx.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={supply.image_url}
          alt={supply.name}
          className="mt-6 max-h-96 w-full rounded-2xl object-cover"
        />
      )}

      {supply.units.length > 0 && (
        <p className="mt-4 text-sm text-muted">
          {t.units}: <strong>{supply.units.join(", ")}</strong>
        </p>
      )}

      {supply.tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1">
          {supply.tags.map((tag) => (
            <Chip key={tag} variant="soft" size="sm">
              {tag}
            </Chip>
          ))}
        </div>
      )}

      {supply.description && (
        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold">{t.descriptionHeading}</h2>
          <CollapsibleMarkdown source={supply.description} />
        </div>
      )}

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/supplies/${supply.id}`}
          entityType="resource"
          entityId={supply.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
