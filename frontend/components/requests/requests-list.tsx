"use client";

import { Card, Chip } from "@heroui/react";
import Link from "next/link";
import { useState } from "react";

import { useI18n } from "@/i18n/provider";
import { markdownToExcerpt } from "@/lib/markdown-excerpt";
import type { HelpState, RequestListEntry } from "@/lib/requests.api";

const HELP_STATE_COLOR: Record<HelpState, "success" | "default" | "warning"> = {
  needs_help: "warning",
  committed: "default",
  completed: "success",
};

const FILTER_KEYS = ["all", "needs_help", "committed", "completed"] as const;
type CampaignFilter = (typeof FILTER_KEYS)[number];

/** Public list of campaigns (Requests) as a responsive grid of cards. */
export function RequestsList({ requests }: { requests: RequestListEntry[] }) {
  const { dict, locale } = useI18n();
  const t = dict.requests;
  const filterT = dict.requestItem.filters;
  const helpStateT = dict.requestItem.helpState;
  const [filter, setFilter] = useState<CampaignFilter>("all");

  const visible =
    filter === "all"
      ? requests
      : requests.filter((request) => request.help_state === filter);

  function formatDay(iso: string): string {
    const dt = new Date(iso);
    if (Number.isNaN(dt.getTime())) {
      return iso;
    }
    return dt.toLocaleDateString(locale === "es" ? "es-ES" : "en-US", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap gap-2">
        {FILTER_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            aria-pressed={filter === key}
            className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
              filter === key
                ? "bg-[color:var(--accent-strong)] text-white"
                : "bg-default-100 text-foreground hover:bg-default-200"
            }`}
          >
            {filterT[key]}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <Card variant="transparent" className="py-12 text-center">
          <Card.Content>
            <p className="text-muted">{t.empty}</p>
          </Card.Content>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((request) => (
            <Link
              key={request.id}
              href={`/requests/${request.id}`}
              className="rounded-2xl transition-shadow hover:shadow-md"
              aria-label={`${t.viewDetails} ${request.title}`}
            >
              <Card className="h-full">
                {request.image_url && (
                  // External, user-supplied image URL: next/image would need
                  // every host allow-listed, so a plain img is pragmatic here.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={request.image_url}
                    alt={request.title}
                    className="h-40 w-full rounded-t-2xl object-cover"
                  />
                )}
                <Card.Header>
                  <Card.Title>{request.title}</Card.Title>
                  {request.description && (
                    <Card.Description className="line-clamp-3">
                      {markdownToExcerpt(request.description)}
                    </Card.Description>
                  )}
                </Card.Header>
                <Card.Footer className="flex flex-wrap items-center gap-2">
                  <Chip
                    color={HELP_STATE_COLOR[request.help_state]}
                    variant="soft"
                    size="sm"
                  >
                    {helpStateT[request.help_state]}
                  </Chip>
                  <span className="text-xs text-muted">
                    {t.lastActivity}: {formatDay(request.last_activity_at)}
                  </span>
                </Card.Footer>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
