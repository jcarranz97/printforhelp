"use client";

import { Alert, Button } from "@heroui/react";
import { useState, useTransition } from "react";

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

  const commentById = new Map(comments.map((c) => [c.id, c]));
  const actionLabel: Record<string, string> = t.actions;

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

  function changeSummary(entry: ActivityEntry): string | null {
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

            return (
              <li key={entry.id} className="flex gap-3">
                <div className="mt-1 flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
                  {entry.actor.username.slice(0, 1)}
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <p className="text-xs text-muted">
                    <span className="font-medium text-foreground">
                      {entry.actor.username}
                    </span>{" "}
                    {actionLabel[entry.action] ?? entry.action}
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
                      <Markdown source={comment.body} />
                      {(canEdit || canDelete) && (
                        <div className="flex gap-3 text-xs">
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
                      )}
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
