import { EntityFeed, type FeedViewer } from "@/components/comments/entity-feed";
import { getServerI18n } from "@/i18n/server";
import type { ActivityEntry, Comment } from "@/lib/feed.api";

/**
 * The campaign's **private** moderation thread: the reviewer's questions, the
 * author's answers, and every verdict, on one timeline.
 *
 * Deliberately a separate entity (`request_review`) from the campaign's own
 * public comments, keyed on the same campaign id. Publishing a campaign must
 * not publish the conversation that vetted it — so this thread stays visible
 * only to the requesters and maintainers/admins, forever, and never mixes into
 * the public feed further down the page.
 *
 * Only rendered for people who may see it; the API enforces the same rule.
 */
export async function ReviewThread({
  requestId,
  comments,
  activity,
  viewer,
}: {
  requestId: string;
  comments: Comment[];
  activity: ActivityEntry[];
  viewer: FeedViewer;
}) {
  const { dict } = await getServerI18n();
  const t = dict.moderation;

  return (
    <section
      id="review"
      className="mt-6 flex scroll-mt-24 flex-col gap-3 rounded-2xl border px-4 py-4"
      style={{ borderColor: "var(--card-border)" }}
    >
      <div>
        <h2 className="text-base font-semibold">{t.discussionTitle}</h2>
        <p className="text-sm text-muted">{t.discussionSubtitle}</p>
      </div>
      <EntityFeed
        revalidate={`/requests/${requestId}`}
        entityType="request_review"
        entityId={requestId}
        comments={comments}
        activity={activity}
        viewer={viewer}
        // No reactions or reply threads in the confidential moderation thread —
        // it stays a simple linear reviewer/author conversation.
        allowReactions={false}
        allowReplies={false}
      />
    </section>
  );
}
