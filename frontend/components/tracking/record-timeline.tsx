"use client";

import { Card, Chip } from "@heroui/react";
import { useMemo } from "react";

import { Markdown } from "@/components/comments/markdown";
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
}: {
  records: TrackingRecord[];
  revalidate: string;
  /** When true, chips out which unit (item) each record belongs to. */
  showItemSequence?: boolean;
}) {
  const { dict, locale } = useI18n();
  const t = dict.tracking;

  // Distinct tags across all records, for the tag-editor autocomplete.
  const allTags = useMemo(
    () =>
      Array.from(new Set(records.flatMap((r) => r.tags))).sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [records, locale],
  );

  if (records.length === 0) {
    return <p className="text-sm text-muted">{t.timelineEmpty}</p>;
  }

  return (
    <div className="flex flex-col gap-3">
      {records.map((record) => (
        <Card key={record.id}>
          <Card.Content className="flex flex-col gap-2 py-3">
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
              <span className="font-medium text-foreground">
                {record.author.username ?? t.anonymous}
              </span>
              <span>{formatDateTime(record.created_at, locale)}</span>
            </div>
            <Markdown source={record.description} />
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
          </Card.Content>
        </Card>
      ))}
    </div>
  );
}
