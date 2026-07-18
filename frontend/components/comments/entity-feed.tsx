"use client";

import { Alert, Button } from "@heroui/react";
import { useEffect, useState, useTransition } from "react";

import {
  deleteCommentAction,
  editCommentAction,
  postCommentAction,
} from "@/actions/feed.action";
import { fetchReactionStatesAction } from "@/actions/reactions.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { LikeButton } from "@/components/reactions/like-button";
import { useI18n } from "@/i18n/provider";
import type { ActivityEntry, Comment, EntityType } from "@/lib/feed.api";

import { Markdown } from "./markdown";

export type FeedViewer = { id: string; role: string } | null;

type EntityFeedProps = {
  /** The page route to revalidate after a mutation (center or shipment). */
  revalidate: string;
  entityType: EntityType;
  entityId: string;
  comments: Comment[];
  activity: ActivityEntry[];
  viewer: FeedViewer;
  /**
   * Parent-owned deep link. When this prop is passed (even as `null`), the feed
   * stops reading `window.location.hash` itself — the parent decides which
   * comment to highlight and handles scrolling. A non-null value highlights
   * that comment. Omit it (the default) to keep the self-contained hash
   * behavior used by pages without a parent coordinator (e.g. center pages).
   */
  deepLinkCommentId?: string | null;
  /**
   * Parent-owned deep link to a lifecycle entry (a status change), the
   * activity-timeline analogue of `deepLinkCommentId`. When set, that entry is
   * highlighted — and, in `commentsOnly` mode, surfaced even though lifecycle
   * entries are otherwise hidden — so a "changed the status" notification lands
   * on the exact change. Passing either deep-link prop (even `null`) makes the
   * feed parent-controlled and stops it reading the URL hash itself.
   */
  deepLinkRecordId?: string | null;
  /**
   * Hide lifecycle/activity entries and show only comments. Used for request
   * items, whose commitment events ("committed to print", "updated their
   * commitment") are noise here — the "Commitments" section already tracks who
   * is collaborating and with how many.
   */
  commentsOnly?: boolean;
  /**
   * Whether each comment shows a like (reaction) button. Defaults to true;
   * the private moderation review thread passes false so reactions never
   * appear in that confidential space.
   */
  allowReactions?: boolean;
};

function formatWhen(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

/**
 * Public community timeline for one entity (a center or a shipment):
 * lifecycle activity merged with Markdown comments (FR-131 – FR-133).
 * Reads are public; the composer and edit/delete controls only appear
 * for authenticated viewers and call server actions (the backend is the
 * real authorization boundary).
 */
export function EntityFeed({
  revalidate,
  entityType,
  entityId,
  comments,
  activity,
  viewer,
  deepLinkCommentId,
  deepLinkRecordId,
  commentsOnly = false,
  allowReactions = true,
}: EntityFeedProps) {
  const { dict, locale } = useI18n();
  const t = dict.feed;
  const isAuthenticated = viewer !== null;
  const [body, setBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingBody, setEditingBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  // Per-comment like state, fetched client-side (one batch call) so the
  // eight pages that render this feed need no extra server wiring. Keyed by
  // comment id; missing entries fall back to a zero, un-reacted heart.
  const [reactions, setReactions] = useState<
    Record<string, { count: number; reacted: boolean }>
  >({});

  const commentById = new Map(comments.map((c) => [c.id, c]));
  // Stable dependency so the effect only refetches when the comment set
  // actually changes (e.g. after posting or deleting one).
  const commentIdsKey = comments.map((c) => c.id).join(",");
  useEffect(() => {
    if (!allowReactions) {
      return;
    }
    const ids = commentIdsKey ? commentIdsKey.split(",") : [];
    if (ids.length === 0) {
      setReactions({});
      return;
    }
    let cancelled = false;
    void fetchReactionStatesAction("comment", ids).then((map) => {
      if (!cancelled) {
        setReactions(map);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [commentIdsKey, allowReactions]);
  const actionLabel: Record<string, string> = t.actions;
  // In comments-only mode, drop every non-comment lifecycle entry so the
  // timeline is just the discussion (commitment churn lives in "Commitments") —
  // except the one status entry a notification deep-linked to, which we surface
  // (highlighted) so "changed the status" clicks have something to land on.
  const visibleActivity = commentsOnly
    ? activity.filter(
        (entry) =>
          entry.action === "commented" ||
          entry.id === deepLinkRecordId ||
          entry.id === highlightId,
      )
    : activity;

  // Deep-link support. When a parent owns the deep link (`deepLinkCommentId`
  // passed), honor only that explicit target and never touch the URL hash —
  // the parent coordinates reveal + scroll, and a stale hash (e.g. one the
  // router cache restores on a return visit) must not re-trigger a highlight.
  // Otherwise (prop omitted) fall back to reading `#comment-<id>` ourselves,
  // for pages with no coordinator (center/shipment feeds).
  const parentControlled =
    deepLinkCommentId !== undefined || deepLinkRecordId !== undefined;
  useEffect(() => {
    if (parentControlled) {
      if (deepLinkCommentId) {
        setHighlightId(deepLinkCommentId);
      } else if (deepLinkRecordId) {
        setHighlightId(deepLinkRecordId);
      }
      return;
    }
    // Self-contained pages (center/shipment/part feeds) read the hash: a
    // comment permalink is `#comment-<id>`; a status-change notification is
    // `#record-<id>` (the activity row's id), scrolled to the same way.
    function applyHash() {
      const hash = window.location.hash;
      const prefix = hash.startsWith("#comment-")
        ? "#comment-"
        : hash.startsWith("#record-")
          ? "#record-"
          : null;
      if (prefix === null) {
        return;
      }
      const id = hash.slice(prefix.length);
      const domId = `${prefix.slice(1)}${id}`;
      setHighlightId(id);
      requestAnimationFrame(() => {
        document
          .getElementById(domId)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, [parentControlled, deepLinkCommentId, deepLinkRecordId]);

  // Clear the highlight a few seconds after it is applied.
  useEffect(() => {
    if (highlightId === null) {
      return;
    }
    const timer = setTimeout(() => setHighlightId(null), 3000);
    return () => clearTimeout(timer);
  }, [highlightId]);

  async function copyLink(commentId: string) {
    const url = `${window.location.origin}${window.location.pathname}#comment-${commentId}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard may be unavailable (insecure context); fall back to the
      // hash so the address bar still holds a copyable permalink.
      window.location.hash = `comment-${commentId}`;
    }
    setCopiedId(commentId);
    setTimeout(() => setCopiedId((id) => (id === commentId ? null : id)), 2000);
  }

  function submit() {
    if (!body.trim() || isPending) {
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await postCommentAction(
        revalidate,
        entityType,
        entityId,
        body,
      );
      if (res.error) {
        setError(res.error);
      } else {
        setBody("");
      }
    });
  }

  function saveEdit(commentId: string) {
    if (!editingBody.trim() || isPending) {
      return;
    }
    setError(null);
    startTransition(async () => {
      const res = await editCommentAction(revalidate, commentId, editingBody);
      if (res.error) {
        setError(res.error);
      } else {
        setEditingId(null);
        setEditingBody("");
      }
    });
  }

  function remove(commentId: string) {
    setError(null);
    startTransition(async () => {
      const res = await deleteCommentAction(revalidate, commentId);
      if (res.error) {
        setError(res.error);
      }
    });
  }

  function statusLabel(value: unknown): string {
    if (typeof value === "string" && value in dict.shipments.status) {
      return dict.shipments.status[value as keyof typeof dict.shipments.status];
    }
    return String(value);
  }

  const commitmentStatus = t.commitmentStatus;
  const moderationStatus = dict.moderation.status;

  function commitmentLabel(value: string): string {
    return value in commitmentStatus
      ? commitmentStatus[value as keyof typeof commitmentStatus]
      : value;
  }

  // A commitment event on a request item's timeline carries a `quantity` and,
  // for status changes, the new contribution status under `status.to`. A
  // `created` event is the initial claim. Rendered as "<status> · <n> pcs".
  // An `updated` event is a resized commitment: `quantity` is `{from, to}`.
  function commitmentSummary(entry: ActivityEntry): string | null {
    if (entry.entity_type !== "request_item") {
      return null;
    }
    if (entry.action === "updated") {
      const change = entry.changes.quantity as
        | { from?: number; to?: number }
        | undefined;
      if (typeof change?.from === "number" && typeof change.to === "number") {
        return `${change.from} → ${change.to} ${t.commitmentUnit}`;
      }
      return null;
    }
    let toStatus: string | null = null;
    if (entry.action === "created") {
      toStatus = "claimed";
    } else if (entry.action === "status_changed") {
      const change = entry.changes.status as { to?: string } | undefined;
      toStatus = change?.to ?? null;
    }
    if (toStatus === null) {
      return null;
    }
    const label = commitmentLabel(toStatus);
    const qty = entry.changes.quantity;
    return typeof qty === "number"
      ? `${label} · ${qty} ${t.commitmentUnit}`
      : label;
  }

  function changeSummary(entry: ActivityEntry): string | null {
    const commitment = commitmentSummary(entry);
    if (commitment !== null) {
      return commitment;
    }
    // A review verdict on a campaign: `{moderation: {from, to}}`. Rendered in
    // the same timeline as the comments so the review reads as one thread.
    const moderation = entry.changes.moderation as
      | { from?: string; to?: string }
      | undefined;
    if (moderation?.from && moderation.to) {
      const label = (key: string): string =>
        key in moderationStatus
          ? moderationStatus[key as keyof typeof moderationStatus]
          : key;
      return `${label(moderation.from)} → ${label(moderation.to)}`;
    }
    if (entry.action === "item_added") {
      const name = entry.changes.resource_name;
      return typeof name === "string" ? name : null;
    }
    if (entry.action === "status_changed") {
      const change = entry.changes.status as
        | { from: string; to: string }
        | undefined;
      if (change) {
        return `${statusLabel(change.from)} → ${statusLabel(change.to)}`;
      }
    }
    return null;
  }

  // For request-item commitment events, use commitment-specific verbs
  // ("committed to print") instead of the generic "created this".
  function actionText(entry: ActivityEntry): string {
    if (
      entry.entity_type === "request_item" &&
      (entry.action === "created" ||
        entry.action === "status_changed" ||
        entry.action === "updated")
    ) {
      return t.itemActions[entry.action];
    }
    return actionLabel[entry.action] ?? entry.action;
  }

  return (
    <div className="flex flex-col gap-4">
      {viewer ? (
        <div className="flex flex-col gap-2">
          <MarkdownEditor
            ariaLabel={t.composerPlaceholder}
            rows={3}
            placeholder={t.composerPlaceholder}
            value={body}
            onChange={setBody}
            onSubmit={submit}
          />
          <div className="flex items-center justify-end gap-2">
            <Button
              size="sm"
              isPending={isPending}
              isDisabled={!body.trim()}
              onPress={submit}
            >
              {t.post}
            </Button>
          </div>
        </div>
      ) : (
        <p className="text-sm text-muted">{t.loginToComment}</p>
      )}

      {error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      {visibleActivity.length === 0 ? (
        <p className="text-sm text-muted">
          {commentsOnly ? t.emptyComments : t.empty}
        </p>
      ) : (
        <ul className="flex flex-col gap-4">
          {visibleActivity.map((entry) => {
            const commentId =
              typeof entry.changes.comment_id === "string"
                ? entry.changes.comment_id
                : undefined;
            const comment = commentId ? commentById.get(commentId) : undefined;
            const isCommentEvent =
              entry.action === "commented" && comment !== undefined;
            const canEdit =
              comment && viewer && comment.author.id === viewer.id;
            const canDelete =
              comment &&
              viewer &&
              (comment.author.id === viewer.id ||
                viewer.role === "maintainer" ||
                viewer.role === "admin");
            const summary = changeSummary(entry);

            // Comment events anchor on the comment id; every other entry (a
            // status change) anchors on its own activity-row id as `record-<id>`
            // so a "changed the status" notification can scroll to it.
            const isHighlighted = isCommentEvent
              ? comment.id === highlightId
              : entry.id === highlightId;

            return (
              <li
                key={entry.id}
                id={
                  isCommentEvent
                    ? `comment-${comment.id}`
                    : `record-${entry.id}`
                }
                className={`flex scroll-mt-24 gap-3 rounded-lg transition-colors ${
                  isHighlighted
                    ? "-mx-2 bg-default-100 px-2 py-1 ring-2 ring-[color:var(--accent-strong)]"
                    : ""
                }`}
              >
                <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
                  {entry.actor.username.slice(0, 1)}
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <p className="text-xs text-muted">
                    <span className="font-medium text-foreground">
                      {entry.actor.username}
                    </span>{" "}
                    {actionText(entry)}
                    {" · "}
                    {formatWhen(entry.created_at, locale)}
                    {comment?.edited_at && ` · ${t.edited}`}
                  </p>

                  {isCommentEvent && editingId === comment.id ? (
                    <div className="flex flex-col gap-2">
                      <MarkdownEditor
                        ariaLabel={t.composerPlaceholder}
                        rows={3}
                        value={editingBody}
                        onChange={setEditingBody}
                        onSubmit={() => saveEdit(comment.id)}
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          isPending={isPending}
                          onPress={() => saveEdit(comment.id)}
                        >
                          {t.save}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onPress={() => {
                            setEditingId(null);
                            setEditingBody("");
                          }}
                        >
                          {t.cancel}
                        </Button>
                      </div>
                    </div>
                  ) : isCommentEvent ? (
                    <>
                      <Markdown
                        source={comment.body}
                        mentions={comment.mentions}
                      />
                      <div className="flex items-center gap-3 text-xs">
                        {allowReactions && (
                          <LikeButton
                            // Remount when the batched state arrives so the
                            // heart reflects the fetched count/reacted values.
                            key={`like-${comment.id}-${
                              reactions[comment.id]?.count ?? 0
                            }-${reactions[comment.id]?.reacted ?? false}`}
                            entityType="comment"
                            entityId={comment.id}
                            initialCount={reactions[comment.id]?.count ?? 0}
                            initialReacted={
                              reactions[comment.id]?.reacted ?? false
                            }
                            isAuthenticated={isAuthenticated}
                          />
                        )}
                        <button
                          type="button"
                          className="text-muted hover:text-foreground"
                          onClick={() => void copyLink(comment.id)}
                        >
                          {copiedId === comment.id ? t.linkCopied : t.copyLink}
                        </button>
                        {canEdit && (
                          <button
                            type="button"
                            className="text-muted hover:text-foreground"
                            onClick={() => {
                              setEditingId(comment.id);
                              setEditingBody(comment.body);
                            }}
                          >
                            {t.edit}
                          </button>
                        )}
                        {canDelete && (
                          <button
                            type="button"
                            className="text-danger hover:underline"
                            onClick={() => remove(comment.id)}
                          >
                            {t.delete}
                          </button>
                        )}
                      </div>
                    </>
                  ) : (
                    summary && (
                      <p className="text-sm text-foreground">{summary}</p>
                    )
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
