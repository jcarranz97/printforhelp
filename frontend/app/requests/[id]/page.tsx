import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { notFound } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { fetchWatchStateAction } from "@/actions/notifications.action";
import {
  fetchReactionStateAction,
  fetchReactionStatesAction,
} from "@/actions/reactions.action";
import { EntityFeed } from "@/components/comments/entity-feed";
import { LikeButton } from "@/components/reactions/like-button";
import { WatchButton } from "@/components/notifications/watch-button";
import { EntityNoticeBanner } from "@/components/notices/entity-notice-banner";
import { RequestNotice } from "@/components/notices/request-notice";
import type { ItemCenter } from "@/components/requests/item-preferred-centers";
import { ModerationBanner } from "@/components/requests/moderation-banner";
import { ReviewThread } from "@/components/requests/review-thread";
import { RequestDetailView } from "@/components/requests/request-detail";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { getCollectionCenter } from "@/lib/collection-centers.api";
import {
  type ActivityEntry,
  type Comment,
  listActivity,
  listComments,
} from "@/lib/feed.api";
import { listParts } from "@/lib/parts.api";
import {
  getRequest,
  type ItemCommitment,
  listItemCommitments,
} from "@/lib/requests.api";
import {
  resourceImageMap,
  resourceNameMap,
  resourcePackagingMap,
  resourceSourceMap,
  toResourceOptions,
} from "@/lib/resource-options";
import { listSupplies } from "@/lib/supplies.api";

export async function generateMetadata(): Promise<Metadata> {
  const { dict } = await getServerI18n();
  return { title: `${dict.requests.title} · PrintForHelp` };
}

export default async function RequestDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string; fromItem?: string }>;
}) {
  const { id } = await params;
  const { from, fromItem } = await searchParams;
  // The token is what makes an unpublished campaign readable to its author and
  // to maintainers; without it the API 404s and this page falls through to
  // notFound() — which is exactly what a leaked link should do for everyone
  // else.
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  const request = await getRequest(id, token);
  if (!request) {
    notFound();
  }

  const user = await getCurrentUser();
  const { dict } = await getServerI18n();
  const isMaintainer = user?.role === "maintainer" || user?.role === "admin";
  // Requesters and maintainers/admins — the only people who ever see the
  // review thread, published or not.
  const canSeeReview =
    !!user && (user.id === request.requester_user_id || isMaintainer);
  const [
    parts,
    supplies,
    comments,
    activity,
    watching,
    reaction,
    itemReactions,
    reviewComments,
    reviewActivity,
  ] = await Promise.all([
    listParts(),
    listSupplies(),
    listComments("request", request.id, token),
    listActivity("request", request.id, token),
    user
      ? fetchWatchStateAction("request", request.id)
      : Promise.resolve(false),
    fetchReactionStateAction("request", request.id),
    fetchReactionStatesAction(
      "request_item",
      request.items.map((item) => item.id),
    ),
    // The private moderation thread — a separate timeline on the same id. The
    // API returns nothing to anyone who may not see it; we skip the round trip
    // entirely for those viewers.
    canSeeReview
      ? listComments("request_review", request.id, token)
      : Promise.resolve([]),
    canSeeReview
      ? listActivity("request_review", request.id, token)
      : Promise.resolve([]),
  ]);

  // Names cover every referenced resource (incl. discontinued) so existing
  // items still label correctly.
  const resourceNames = resourceNameMap(parts, supplies);
  // External source/download URL per resource, so each item can offer the
  // "Take me to MakerWorld" / download CTA right on the campaign page.
  const resourceSources = resourceSourceMap(parts, supplies);
  // Catalog image per resource, so each item shows a preview of the part a
  // maker will be printing right on the campaign page.
  const resourceImages = resourceImageMap(parts, supplies);
  // Packaging guidance per resource, so each item card can show the "how to
  // package this" panel inline instead of on the per-item page.
  const resourcePackaging = resourcePackagingMap(parts, supplies);

  // Resolve the request's preferred drop-off centers once — the shared
  // candidate set every item's "drop-off centers" panel narrows down from —
  // and fetch each item's public commitments, so the cards carry everything
  // that used to require opening the per-item view.
  const [
    centerCandidatesRaw,
    commitmentLists,
    itemCommentLists,
    itemActivityLists,
  ] = await Promise.all([
    Promise.all(
      (request.preferred_collection_center_ids ?? []).map((cid) =>
        getCollectionCenter(cid),
      ),
    ),
    Promise.all(
      request.items.map((item) =>
        listItemCommitments(request.id, String(item.item_number), token),
      ),
    ),
    // Per-item comment thread + activity timeline (entity type "request_item"),
    // so each card can host the "Comments & activity" panel the retired item
    // page used to own. Unpublished campaigns gate these by viewer server-side.
    Promise.all(
      request.items.map((item) => listComments("request_item", item.id, token)),
    ),
    Promise.all(
      request.items.map((item) => listActivity("request_item", item.id, token)),
    ),
  ]);
  const centerCandidates: ItemCenter[] = centerCandidatesRaw
    .filter((c): c is NonNullable<typeof c> => c !== null)
    .map((c) => ({
      id: c.id,
      name: c.name,
      city: c.city,
      country: c.country,
      location_url: c.location_url,
    }));
  const commitmentsByItem: Record<string, ItemCommitment[]> = {};
  const commentsByItem: Record<string, Comment[]> = {};
  const activityByItem: Record<string, ActivityEntry[]> = {};
  request.items.forEach((item, index) => {
    commitmentsByItem[item.id] = commitmentLists[index];
    commentsByItem[item.id] = itemCommentLists[index];
    activityByItem[item.id] = itemActivityLists[index];
  });
  // Only active, non-discontinued 3D parts can be added as new items.
  // Supplies were retired from the requests flow: existing supply items still
  // render (their names come from the maps above), but no new ones are offered.
  const activeResources = toResourceOptions(
    parts.filter((part) => part.active && part.status === "active"),
    [],
  );

  const canManage = canSeeReview;
  const viewer = user ? { id: user.id, role: user.role } : null;
  const t = dict.requestDetail;
  // Contextual back link based on where the visitor came from:
  // - from an item page (`?from=item&fromItem=N`) → back to that item
  // - from My Contributions (`?from=contributions`) → back there
  // - otherwise → the public requests list
  const fromItemNav = from === "item" && !!fromItem;
  const fromContributions = from === "contributions";
  let backHref = "/requests";
  let backLabel = t.back;
  if (fromItemNav) {
    const originItem = request.items.find(
      (i) => String(i.item_number) === fromItem,
    );
    const originName = originItem
      ? (resourceNames[originItem.resource_id] ?? "")
      : "";
    backHref = `/requests/${id}/items/${fromItem}`;
    backLabel = `← ${t.backToItem} ${originName} #${fromItem}`;
  } else if (fromContributions) {
    backHref = "/my-contributions";
    backLabel = t.backToContributions;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <div className="flex items-center justify-between gap-4">
        <Link href={backHref} className="text-sm text-muted hover:underline">
          {backLabel}
        </Link>
        <div className="flex items-center gap-2">
          <LikeButton
            entityType="request"
            entityId={request.id}
            initialCount={reaction.count}
            initialReacted={reaction.reacted}
            isAuthenticated={!!user}
          />
          {user && (
            <WatchButton
              entityType="request"
              entityId={request.id}
              initialWatching={watching}
            />
          )}
        </div>
      </div>
      <div className="mt-4">
        <ModerationBanner
          requestId={request.id}
          status={request.moderation_status}
          canManage={canManage}
          isMaintainer={isMaintainer}
        />
      </div>
      {canSeeReview && (
        <ReviewThread
          requestId={request.id}
          comments={reviewComments}
          activity={reviewActivity}
          viewer={viewer}
        />
      )}
      <EntityNoticeBanner targetType="request" targetId={request.id} />
      {canManage && (
        <RequestNotice
          targetType="request"
          targetId={request.id}
          revalidate={`/requests/${request.id}`}
          isMaintainer={isMaintainer}
        />
      )}

      <div className="mt-6">
        <RequestDetailView
          request={request}
          resources={activeResources}
          resourceNames={resourceNames}
          resourceSources={resourceSources}
          resourceImages={resourceImages}
          resourcePackaging={resourcePackaging}
          centerCandidates={centerCandidates}
          commitmentsByItem={commitmentsByItem}
          commentsByItem={commentsByItem}
          activityByItem={activityByItem}
          viewer={viewer}
          currentUsername={user?.username ?? null}
          isLoggedIn={!!user}
          canManage={canManage}
          initialWatching={watching}
          itemReactions={itemReactions}
        />
      </div>

      {/* The campaign's PUBLIC comment feed. The review conversation lives in
          its own private thread above and never merges into this one, so
          publishing a campaign does not publish its review. */}
      <section className="mt-10 flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t.feedTitle}</h2>
          <p className="text-sm text-muted">{t.feedSubtitle}</p>
        </div>
        <EntityFeed
          revalidate={`/requests/${request.id}`}
          entityType="request"
          entityId={request.id}
          comments={comments}
          activity={activity}
          viewer={viewer}
        />
      </section>
    </main>
  );
}
