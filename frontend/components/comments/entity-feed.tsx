"use client";

import { Alert, Button } from "@heroui/react";
import { useEffect, useState, useTransition } from "react";

import {
  deleteCommentAction,
  editCommentAction,
  postCommentAction,
} from "@/actions/feed.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
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
}: EntityFeedProps) {
  const { dict, locale } = useI18n();
  const t = dict.feed;
  const [body, setBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingBody, setEditingBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const commentById = new Map(comments.map((c) => [c.id, c]));
  const actionLabel: Record<string, string> = t.actions;

  // Deep-link support: when the URL carries `#comment-<id>` (e.g. from a
  // notification or a copied permalink), scroll to that comment and flash a
  // highlight. Runs on mount and on later hash changes (same-page links).
  useEffect(() => {
    function applyHash() {
      const hash = window.location.hash;
      if (!hash.startsWith("#comment-")) {
        return;
      }
      const id = hash.slice("#comment-".length);
      setHighlightId(id);
      requestAnimationFrame(() => {
        document
          .getElementById(`comment-${id}`)
          ?.scrollIntoView({ behavior: "smooth", block: "center" });
      });
    }
    applyHash();
    window.addEventListener("hashchange", applyHash);
    return () => window.removeEventListener("hashchange", applyHash);
  }, []);

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
    if (!body.trim()) {
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
    if (!editingBody.trim()) {
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

  function commitmentLabel(value: string): string {
    return value in commitmentStatus
      ? commitmentStatus[value as keyof typeof commitmentStatus]
      : value;
  }

  // A commitment event on a request item's timeline carries a `quantity` and,
  // for status changes, the new contribution status under `status.to`. A
  // `created` event is the initial claim. Rendered as "<status> · <n> pcs".
  function commitmentSummary(entry: ActivityEntry): string | null {
    if (entry.entity_type !== "request_item") {
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
      (entry.action === "created" || entry.action === "status_changed")
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

      {activity.length === 0 ? (
        <p className="text-sm text-muted">{t.empty}</p>
      ) : (
        <ul className="flex flex-col gap-4">
          {activity.map((entry) => {
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

            const isHighlighted = isCommentEvent && comment.id === highlightId;

            return (
              <li
                key={entry.id}
                id={isCommentEvent ? `comment-${comment.id}` : undefined}
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
                      <div className="flex gap-3 text-xs">
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
