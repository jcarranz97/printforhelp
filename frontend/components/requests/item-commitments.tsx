"use client";

import { Chip } from "@heroui/react";

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
 * Public list of commitments on a request item: who has already committed,
 * how many, and where they are in the lifecycle. Notes/tags are private and
 * never shown here. Reads are public so the shareable link is transparent.
 */
export function ItemCommitments({
  commitments,
}: {
  commitments: ItemCommitment[];
}) {
  const { dict } = useI18n();
  const t = dict.requestItem;

  if (commitments.length === 0) {
    return <p className="text-sm text-muted">{t.commitmentsEmpty}</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {commitments.map((c) => (
        <li
          key={c.id}
          className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2"
          style={{ borderColor: "var(--card-border)" }}
        >
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-default-100 text-xs font-semibold uppercase">
              {c.maker_username.slice(0, 1)}
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{c.maker_username}</p>
              {c.collection_center_name && (
                <p className="truncate text-xs text-muted">
                  {c.collection_center_name}
                </p>
              )}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span className="text-sm">
              <strong>{c.quantity}</strong> {t.commitmentUnit}
            </span>
            <Chip variant="soft" size="sm" color={STATUS_COLOR[c.status]}>
              {t.commitmentStatus[c.status]}
            </Chip>
          </div>
        </li>
      ))}
    </ul>
  );
}
