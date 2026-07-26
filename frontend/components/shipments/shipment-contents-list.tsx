"use client";

import { Button, Chip } from "@heroui/react";
import Link from "next/link";

import { UserAvatar } from "@/components/common/user-avatar";
import { useI18n } from "@/i18n/provider";
import type { ContributionStatus } from "@/lib/contributions.api";
import type { ShipmentContentEntry } from "@/lib/shipments.api";

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
 * The manifest lines of a box, shared by the box console and the scan page.
 *
 * Laid out like the commitments list on a request item — one bordered row per
 * line, maker on the left, quantity and status on the right — because that is
 * the same kind of information and staff already read it that way. Cards were
 * far too much furniture for a list someone ticks off against a carton.
 *
 * Purely presentational: the backend only sends lines to a box's custodians
 * (FR-146), so there is nothing to hide here.
 */
export function ShipmentContentsList({
  entries,
  isPending = false,
  onRemove,
}: {
  entries: ShipmentContentEntry[];
  isPending?: boolean;
  onRemove?: (contentId: string) => void;
}) {
  const { dict } = useI18n();
  const t = dict.shipments;
  const statusLabels = dict.myContributions.status;

  if (entries.length === 0) {
    return <p className="text-sm text-muted">{t.contentsEmpty}</p>;
  }

  return (
    <ul className="flex flex-col gap-2">
      {entries.map((entry) => {
        const isBox = entry.kind === "box";
        const token = entry.tracking_token ?? entry.child_tracking_token;
        const status = entry.contribution_status as ContributionStatus | null;
        return (
          <li
            key={entry.id}
            className="flex flex-col gap-2 rounded-lg border px-3 py-2"
            style={{ borderColor: "var(--card-border)" }}
          >
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
              <div className="flex min-w-0 items-center gap-3">
                {isBox ? (
                  <span
                    aria-hidden
                    className="flex size-7 shrink-0 items-center justify-center"
                  >
                    📦
                  </span>
                ) : (
                  <UserAvatar
                    username={entry.maker_username ?? "?"}
                    fullName={entry.maker_full_name}
                    avatarUrl={entry.maker_avatar_url}
                    crop={{
                      x: entry.maker_avatar_crop_x,
                      y: entry.maker_avatar_crop_y,
                      w: entry.maker_avatar_crop_w,
                      h: entry.maker_avatar_crop_h,
                    }}
                    className="size-7"
                    fallbackClassName="text-xs"
                  />
                )}
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    {isBox
                      ? `${t.nestedBox} → ${entry.child_destination ?? "—"}`
                      : (entry.resource_name ?? t.contentsRedacted)}
                  </p>
                  <p className="truncate text-xs text-muted">
                    {isBox
                      ? t.packagesInside.replace(
                          "{count}",
                          String(entry.child_package_count ?? 0),
                        )
                      : entry.maker_username}
                  </p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-2 pl-10 sm:pl-0">
                {!isBox && entry.quantity !== null && (
                  <span className="text-sm">
                    <strong>{entry.quantity}</strong> {t.pieces}
                  </span>
                )}
                {status && (
                  <Chip variant="soft" size="sm" color={STATUS_COLOR[status]}>
                    {statusLabels[status] ?? status}
                  </Chip>
                )}
                {onRemove && (
                  <Button
                    size="sm"
                    variant="danger-soft"
                    isPending={isPending}
                    onPress={() => onRemove(entry.id)}
                  >
                    {t.removeContent}
                  </Button>
                )}
              </div>
            </div>

            {token && (
              <Link
                href={`/track/${token}`}
                className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
              >
                {t.viewQr} →
              </Link>
            )}
          </li>
        );
      })}
    </ul>
  );
}
