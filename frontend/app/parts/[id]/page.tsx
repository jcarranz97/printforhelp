import type { Metadata } from "next";
import { Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import { fetchReactionStateAction } from "@/actions/reactions.action";
import { CollapsibleMarkdown } from "@/components/comments/collapsible-markdown";
import { EntityFeed } from "@/components/comments/entity-feed";
import { LikeButton } from "@/components/reactions/like-button";
import { WatchButton } from "@/components/notifications/watch-button";
import { PART_IMAGE_ASPECT_CSS } from "@/components/parts/part-image-field";
import { EntityNoticeBanner } from "@/components/notices/entity-notice-banner";
import { RequestNotice } from "@/components/notices/request-notice";
import { SourceLinkButton } from "@/components/resources/source-link-button";
import { getServerI18n } from "@/i18n/server";
import { listActivity, listComments } from "@/lib/feed.api";
import { getPart } from "@/lib/parts.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.parts.title} · PrintForHelp` };
}

export default async function PartDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string; fromReq?: string; fromItem?: string }>;
}) {
  const { id } = await params;
  const { from, fromReq, fromItem } = await searchParams;
  const part = await getPart(id);
  if (!part) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const t = dict.partDetail;
  // Contextual back link based on where the visitor came from:
  // - from a request item (`?from=item&fromReq=R&fromItem=N`) → back to it
  // - from My Contributions (`?from=contributions`) → back there
  // - otherwise → the public catalog
  const fromItemNav = from === "item" && !!fromReq && !!fromItem;
  const fromContributions = from === "contributions";
  let backHref = "/parts";
  let backLabel = t.back;
  if (fromItemNav) {
    backHref = `/requests/${fromReq}/items/${fromItem}`;
    backLabel = `← ${t.backToItem} ${part.name} #${fromItem}`;
  } else if (fromContributions) {
    backHref = "/my-contributions";
    backLabel = t.backToContributions;
  }
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  const canEdit = !!user && (user.id === part.owner_user_id || isMaintainer);

  const viewer = user ? { id: user.id, role: user.role } : null;
  const [comments, activity, watching, reaction] = await Promise.all([
    listComments("resource", part.id),
    listActivity("resource", part.id),
    user ? fetchWatchStateAction("resource", part.id) : Promise.resolve(false),
    fetchReactionStateAction("resource", part.id),
  ]);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link href={backHref} className="text-sm text-muted hover:underline">
        {backLabel}
      </Link>

      <div className="mt-6 flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{part.name}</h1>
          {part.status === "discontinued" && (
            <Chip color="warning" variant="soft" size="sm">
              {t.discontinued}
            </Chip>
          )}
        </div>
        <div className="flex items-center gap-2">
          <LikeButton
            entityType="resource"
            entityId={part.id}
            initialCount={reaction.count}
            initialReacted={reaction.reacted}
            isAuthenticated={!!user}
          />
          {user && (
            <WatchButton
              entityType="resource"
              entityId={part.id}
              initialWatching={watching}
            />
          )}
          {canEdit && (
            <Link
              href={`/parts/${part.id}/edit`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.edit}
            </Link>
          )}
        </div>
      </div>

      <EntityNoticeBanner targetType="resource" targetId={part.id} />
      {canEdit && (
        <RequestNotice
          targetType="resource"
          targetId={part.id}
          revalidate={`/parts/${part.id}`}
          isMaintainer={isMaintainer}
        />
      )}

      {part.image_url && (
        // External, user-supplied image URL — see parts-catalog.tsx.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={part.image_url}
          alt={part.name}
          className="mt-6 w-full rounded-2xl object-cover"
          style={{
            aspectRatio: PART_IMAGE_ASPECT_CSS,
            objectPosition: `${part.image_focus_x}% ${part.image_focus_y}%`,
          }}
        />
      )}

      {part.tags.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-1">
          {part.tags.map((tag) => (
            <Chip key={tag} variant="soft" size="sm">
              {tag}
            </Chip>
          ))}
        </div>
      )}

      {part.source_url && (
        <div className="mt-6">
          <SourceLinkButton url={part.source_url} />
        </div>
      )}

      {part.description && (
        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold">{t.descriptionHeading}</h2>
          <CollapsibleMarkdown source={part.description} />
        </div>
      )}

      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/parts/${part.id}`}
          entityType="resource"
          entityId={part.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
