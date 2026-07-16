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
  const { dict } = useI18n();
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
            <div className="flex items-center justify-between gap-3">
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
              <div className="flex shrink-0 items-center gap-2">
                <span className="text-sm">
                  <strong>{c.quantity}</strong> {t.commitmentUnit}
                </span>
                <Chip variant="soft" size="sm" color={STATUS_COLOR[c.status]}>
                  {t.commitmentStatus[c.status]}
                </Chip>
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
