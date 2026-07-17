"use client";

import { Chip } from "@heroui/react";
import Link from "next/link";

import { useI18n } from "@/i18n/provider";
import type { ContributionStatus, ItemCommitment } from "@/lib/requests.api";

const STATUS_COLOR: Record<
  ContributionStatus,
  "default" | "success" | "warning"
> = {
  claimed: "default",
  prepared: "default",
  delivered: "warning",
  received: "success",
  released: "warning",
};

/**
 * Timestamp of the commitment's current lifecycle stage, so readers can see
 * how recently each maker moved it forward. Falls back to earlier stamps if a
 * later one is somehow missing.
 */
function statusDate(c: ItemCommitment): string {
  switch (c.status) {
    case "received":
      return c.received_at ?? c.delivered_at ?? c.prepared_at ?? c.claimed_at;
    case "delivered":
      return c.delivered_at ?? c.prepared_at ?? c.claimed_at;
    case "prepared":
      return c.prepared_at ?? c.claimed_at;
    default:
      return c.claimed_at;
  }
}

/** Format a lifecycle timestamp as a short, locale-aware date. */
function formatStatusDate(iso: string, locale: string): string {
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

/**
 * Public list of commitments on a request item: who has already committed,
 * how many, and where they are in the lifecycle. Notes/tags are private and
 * never shown here. Reads are public so the shareable link is transparent.
 */
export function ItemCommitments({
  commitments,
  currentUsername = null,
}: {
  commitments: ItemCommitment[];
  /** Viewer's username, so their own commitments offer an edit shortcut. */
  currentUsername?: string | null;
}) {
  const { dict, locale } = useI18n();
  const t = dict.requestItem;

  // Released commitments are back-out signals, not real progress — showing
  // them here only confuses readers, so keep them out of the public list.
  const visibleCommitments = commitments.filter((c) => c.status !== "released");

  if (visibleCommitments.length === 0) {
    return <p className="text-sm text-muted">{t.commitmentsEmpty}</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {visibleCommitments.map((c) => {
        // The maker can still resize their own commitment until the units are
        // handed over, so point them at it in "Mis aportes" (FR-057).
        const isMine =
          currentUsername !== null && c.maker_username === currentUsername;
        const canEdit =
          isMine && (c.status === "claimed" || c.status === "prepared");
        return (
          <li
            key={c.id}
            className="flex flex-col gap-2 rounded-lg border px-3 py-2"
            style={{ borderColor: "var(--card-border)" }}
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
                  {c.maker_username.slice(0, 1)}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {c.maker_username}
                  </p>
                  {c.collection_center_name && (
                    <p className="truncate text-xs text-muted">
                      {c.collection_center_name}
                    </p>
                  )}
                </div>
              </div>
              <div className="flex shrink-0 flex-col items-start gap-1 pl-10 sm:items-end sm:pl-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm">
                    <strong>{c.quantity}</strong> {t.commitmentUnit}
                  </span>
                  <Chip variant="soft" size="sm" color={STATUS_COLOR[c.status]}>
                    {t.commitmentStatus[c.status]}
                  </Chip>
                </div>
                <p className="text-xs text-muted">
                  {t.commitmentStatusDate[c.status]}{" "}
                  {formatStatusDate(statusDate(c), locale)}
                </p>
              </div>
            </div>
            {canEdit && (
              <p className="text-xs text-muted">
                {t.editCommitmentPrompt}{" "}
                <Link
                  href={`/my-contributions#contribution-${c.id}`}
                  className="font-medium text-[var(--accent-strong)] hover:underline"
                >
                  {t.editCommitmentLink}
                </Link>
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
