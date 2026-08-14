"use client";

import { Card, Chip } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";

import {
  type ReactionSummary,
  fetchReactionStatesAction,
} from "@/actions/reactions.action";
import { Markdown } from "@/components/comments/markdown";
import { LikeButton } from "@/components/reactions/like-button";
import { useI18n } from "@/i18n/provider";
import type { TrackingRecord } from "@/lib/tracking.api";

import { RecordTagsEditor } from "./record-tags-editor";

/** Format a record timestamp for the timeline. */
function formatDateTime(iso: string, locale: string): string {
  const dt = new Date(iso);
  if (Number.isNaN(dt.getTime())) {
    return iso;
  }
  return dt.toLocaleString(locale === "es" ? "es-ES" : "en-US", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** The list of tracking records (updates), newest first. */
export function RecordTimeline({
  records,
  revalidate,
  showItemSequence = false,
  isAuthenticated = false,
}: {
  records: TrackingRecord[];
  revalidate: string;
  /** When true, chips out which unit (item) each record belongs to. */
  showItemSequence?: boolean;
  /** Whether a session exists; guests see counts and are sent to /login. */
  isAuthenticated?: boolean;
}) {
  const { dict, locale } = useI18n();
  const t = dict.tracking;
  const [highlightId, setHighlightId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [reactions, setReactions] = useState<Record<string, ReactionSummary>>(
    {},
  );

  // Distinct tags across all records, for the tag-editor autocomplete.
  const allTags = useMemo(
    () =>
      Array.from(new Set(records.flatMap((r) => r.tags))).sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [records, locale],
  );

  // Like state for every update on screen, in one round trip. Stable
  // dependency so this only refetches when the record set actually changes
  // (e.g. after posting an update or toggling the item-updates scope).
  const recordIdsKey = records.map((r) => r.id).join(",");
  useEffect(() => {
    const ids = recordIdsKey ? recordIdsKey.split(",") : [];
    if (ids.length === 0) {
      setReactions({});
      return;
    }
    let cancelled = false;
    void fetchReactionStatesAction("tracking_record", ids).then((map) => {
      if (!cancelled) {
        setReactions(map);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [recordIdsKey]);

  // Deep-link support: when the URL carries `#record-<id>` (e.g. from a
  // notification or a copied permalink), scroll to that update and flash a
  // highlight. Runs on mount and on later hash changes (same-page links).
  useEffect(() => {
    function applyHash() {
      const hash = window.location.hash;
      if (!hash.startsWith("#record-")) {
        return;
      }
      const id = hash.slice("#record-".length);
      setHighlightId(id);
      requestAnimationFrame(() => {
        document
          .getElementById(`record-${id}`)
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

  async function copyLink(recordId: string) {
    const url = `${window.location.origin}${window.location.pathname}#record-${recordId}`;
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      // Clipboard may be unavailable (insecure context); fall back to the
      // hash so the address bar still holds a copyable permalink.
      window.location.hash = `record-${recordId}`;
    }
    setCopiedId(recordId);
    setTimeout(() => setCopiedId((id) => (id === recordId ? null : id)), 2000);
  }

  if (records.length === 0) {
    return <p className="text-sm text-muted">{t.timelineEmpty}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {records.map((record) => (
        <div
          key={record.id}
          id={`record-${record.id}`}
          className={`scroll-mt-24 rounded-xl transition-colors ${
            highlightId === record.id
              ? "ring-2 ring-[color:var(--accent-strong)]"
              : ""
          }`}
        >
          <Card>
            <Card.Content className="flex flex-col gap-2 py-3">
              <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                <span className="flex flex-wrap items-center gap-1">
                  <span className="font-medium text-foreground">
                    {record.author.username ?? t.anonymous}
                  </span>
                  {/* The maker of the tracked contribution liked this update —
                      the tracking equivalent of a comment's "liked by author". */}
                  {reactions[record.id]?.byAuthor && (
                    <>
                      {" · "}
                      <span className="whitespace-nowrap font-medium text-foreground">
                        <span className="text-red-500" aria-hidden>
                          ❤
                        </span>{" "}
                        {t.likedByMaker}
                      </span>
                    </>
                  )}
                </span>
                <span>{formatDateTime(record.created_at, locale)}</span>
              </div>
              <Markdown source={record.description} />
              {/* An entry posted above this page's level — on the package, or
                  on a box enclosing it. Badged so a box update is never
                  mistaken for something the maker wrote about this piece. */}
              {record.inherited && (
                <span className="w-fit rounded-full bg-default-100 px-2 py-0.5 text-xs text-muted">
                  {record.origin_level === "shipment"
                    ? `📦 ${t.fromBox}${
                        record.origin_label ? ` · ${record.origin_label}` : ""
                      }`
                    : `📮 ${t.fromPackage}`}
                </span>
              )}
              {showItemSequence && (
                <span className="text-xs text-muted">
                  {record.target_kind === "group"
                    ? t.groupLabel
                    : `${t.itemLabel}${
                        record.item_sequence !== null
                          ? ` #${record.item_sequence}`
                          : ""
                      }`}
                </span>
              )}
              {record.can_edit_tags ? (
                <RecordTagsEditor
                  recordId={record.id}
                  tags={record.tags}
                  allTags={allTags}
                  revalidate={revalidate}
                />
              ) : (
                record.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {record.tags.map((tag) => (
                      <Chip key={tag} variant="soft" size="sm">
                        {tag}
                      </Chip>
                    ))}
                  </div>
                )
              )}
              <div className="flex items-center gap-3 text-xs">
                {/* Remounted when the batched state lands so the heart picks
                    up the server's count instead of staying at zero. */}
                <LikeButton
                  key={`like-${reactions[record.id]?.count ?? 0}-${
                    reactions[record.id]?.reacted ?? false
                  }`}
                  entityType="tracking_record"
                  entityId={record.id}
                  initialCount={reactions[record.id]?.count ?? 0}
                  initialReacted={reactions[record.id]?.reacted ?? false}
                  isAuthenticated={isAuthenticated}
                />
                <button
                  type="button"
                  className="text-muted hover:text-foreground"
                  onClick={() => void copyLink(record.id)}
                >
                  {copiedId === record.id
                    ? t.updateLinkCopied
                    : t.copyUpdateLink}
                </button>
              </div>
            </Card.Content>
          </Card>
        </div>
      ))}
    </div>
  );
}
