"use client";

import { Avatar, Badge, Button, Popover, Separator } from "@heroui/react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { FiSettings } from "react-icons/fi";

import {
  fetchNotificationsAction,
  fetchUnreadCountAction,
  markReadAction,
} from "@/actions/notifications.action";
import { useI18n } from "@/i18n/provider";
import type { Notification } from "@/lib/notifications.api";

const POLL_INTERVAL_MS = 30_000;

type NotificationsMenuProps = {
  username: string;
  initialUnread: number;
};

/**
 * Avatar + unread badge in the top nav. Opening it shows the recent
 * notifications in a popover; clicking one marks it read and navigates to
 * the target. The unread count polls every 30s (a documented SSE upgrade
 * lives in the plan). In-app only for v1.
 */
export function NotificationsMenu({
  username,
  initialUnread,
}: NotificationsMenuProps) {
  const { dict, locale } = useI18n();
  const t = dict.notifications;
  const router = useRouter();

  const [unread, setUnread] = useState(initialUnread);
  const [items, setItems] = useState<Notification[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);

  // Poll the unread count so the badge stays fresh without a page reload.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      const count = await fetchUnreadCountAction();
      if (!cancelled) {
        setUnread(count);
      }
    };
    const id = setInterval(tick, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    const notes = await fetchNotificationsAction({ limit: 15 });
    setItems(notes);
    setLoading(false);
  }, []);

  function onOpenChange(next: boolean) {
    setOpen(next);
    if (next) {
      void load();
    }
  }

  async function openNotification(note: Notification) {
    setOpen(false);
    if (!note.read_at) {
      const count = await markReadAction({ ids: [note.id] });
      setUnread(count);
      setItems(
        (prev) =>
          prev?.map((n) =>
            n.id === note.id ? { ...n, read_at: new Date().toISOString() } : n,
          ) ?? null,
      );
    }
    // Deep-link to the exact item so the target page scrolls to and
    // highlights it: tracking updates carry a ready-made `record-<id>`
    // anchor; comment/mention notifications derive `comment-<id>` from the
    // comment id. Other events land on the entity.
    const anchor =
      note.anchor ?? (note.comment_id ? `comment-${note.comment_id}` : null);
    const target = anchor ? `${note.link}#${anchor}` : note.link;

    // Strip any existing hash first: a same-route navigation would otherwise
    // concatenate the new anchor onto the old one (#comment-a#comment-b).
    if (window.location.hash) {
      window.history.replaceState(
        null,
        "",
        window.location.pathname + window.location.search,
      );
    }

    if (window.location.pathname === note.link) {
      // Already on the target page: set the URL directly and tell the feed
      // to re-scroll/highlight (a same-route router.push would not).
      window.history.replaceState(null, "", target);
      window.dispatchEvent(new Event("hashchange"));
    } else {
      router.push(target);
    }
  }

  async function markAll() {
    const count = await markReadAction({ all: true });
    setUnread(count);
    setItems(
      (prev) =>
        prev?.map((n) => ({
          ...n,
          read_at: n.read_at ?? new Date().toISOString(),
        })) ?? null,
    );
  }

  const initials = username.slice(0, 2).toUpperCase();
  const badgeLabel = unread > 99 ? "99+" : String(unread);

  return (
    <Popover isOpen={open} onOpenChange={onOpenChange}>
      <Popover.Trigger aria-label={t.ariaLabel} className="cursor-pointer">
        {unread > 0 ? (
          <Badge.Anchor>
            <Avatar size="sm" color="accent" variant="soft">
              <Avatar.Fallback>{initials}</Avatar.Fallback>
            </Avatar>
            <Badge color="danger" size="sm">
              {badgeLabel}
            </Badge>
          </Badge.Anchor>
        ) : (
          <Avatar size="sm" color="accent" variant="soft">
            <Avatar.Fallback>{initials}</Avatar.Fallback>
          </Avatar>
        )}
      </Popover.Trigger>
      <Popover.Content className="w-[360px] max-w-[92vw]">
        <Popover.Dialog className="p-0">
          <div className="flex items-center justify-between px-4 py-3">
            <span className="text-sm font-semibold">{t.title}</span>
            {unread > 0 && (
              <button
                type="button"
                className="text-xs text-muted hover:text-foreground"
                onClick={() => void markAll()}
              >
                {t.markAllRead}
              </button>
            )}
          </div>
          <Separator />
          <div className="max-h-[70vh] overflow-y-auto">
            {loading && items === null ? (
              <p className="px-4 py-6 text-center text-sm text-muted">
                {t.loading}
              </p>
            ) : items && items.length > 0 ? (
              <ul className="flex flex-col">
                {items.map((note) => (
                  <li key={note.id}>
                    <button
                      type="button"
                      onClick={() => void openNotification(note)}
                      className={`flex w-full gap-3 border-l-2 px-4 py-3 text-left hover:bg-default-100 ${
                        note.read_at
                          ? "border-transparent"
                          : "border-[color:var(--accent-strong)] bg-default-50"
                      }`}
                    >
                      <div className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
                        {note.actor.username.slice(0, 1)}
                      </div>
                      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                        <p className="text-sm">
                          <span className="font-medium">
                            {note.actor.username}
                          </span>{" "}
                          <span className="text-muted">
                            {summaryVerb(note, t.summary)}
                          </span>
                        </p>
                        <p className="truncate text-sm font-medium text-foreground">
                          {note.title}
                        </p>
                        <p className="text-xs text-muted">
                          {timeAgo(note.created_at, locale)}
                        </p>
                      </div>
                      {!note.read_at && (
                        <span className="mt-2 size-2 shrink-0 rounded-full bg-[color:var(--accent-strong)]" />
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-4 py-6 text-center text-sm text-muted">
                {t.empty}
              </p>
            )}
          </div>
          <Separator />
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              router.push("/settings/notifications");
            }}
            className="flex w-full items-center gap-2 px-4 py-3 text-left text-sm text-muted hover:bg-default-100 hover:text-foreground"
          >
            <FiSettings className="size-4 shrink-0" aria-hidden />
            {t.configure}
          </button>
        </Popover.Dialog>
      </Popover.Content>
    </Popover>
  );
}

function summaryVerb(
  note: Notification,
  summary: {
    mentioned: string;
    commented: string;
    statusChanged: string;
    itemAdded: string;
    trackingUpdate: string;
    requestSubmitted: string;
    requestReviewed: string;
    updated: string;
    reaction: Record<string, string>;
  },
): string {
  if (note.reason === "mention") {
    return summary.mentioned;
  }
  if (note.event === "commented") {
    return summary.commented;
  }
  if (note.event === "status_changed") {
    return summary.statusChanged;
  }
  if (note.event === "item_added") {
    return summary.itemAdded;
  }
  if (note.event === "tracking_update") {
    return summary.trackingUpdate;
  }
  if (note.event === "request_submitted") {
    return summary.requestSubmitted;
  }
  if (note.event === "request_reviewed") {
    return summary.requestReviewed;
  }
  if (note.event === "reaction") {
    // Tailor the verb to what was liked (part, request, comment, …).
    return summary.reaction[note.entity_type] ?? summary.reaction.default;
  }
  return summary.updated;
}

const DIVISIONS: { amount: number; unit: Intl.RelativeTimeFormatUnit }[] = [
  { amount: 60, unit: "second" },
  { amount: 60, unit: "minute" },
  { amount: 24, unit: "hour" },
  { amount: 7, unit: "day" },
  { amount: 4.34524, unit: "week" },
  { amount: 12, unit: "month" },
  { amount: Number.POSITIVE_INFINITY, unit: "year" },
];

function timeAgo(iso: string, locale: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  const rtf = new Intl.RelativeTimeFormat(locale === "es" ? "es" : "en", {
    numeric: "auto",
  });
  let duration = (date.getTime() - Date.now()) / 1000;
  for (const division of DIVISIONS) {
    if (Math.abs(duration) < division.amount) {
      return rtf.format(Math.round(duration), division.unit);
    }
    duration /= division.amount;
  }
  return iso;
}
