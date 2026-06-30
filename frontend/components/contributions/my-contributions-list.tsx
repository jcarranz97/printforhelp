"use client";

import { Button, Card, Chip } from "@heroui/react";
import Link from "next/link";

import { advanceContributionAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";
import type {
  ContributionStatus,
  MyContribution,
} from "@/lib/contributions.api";

import { type CenterOption, SetCenterForm } from "./set-center-form";

const STATUS_COLOR: Record<
  ContributionStatus,
  "default" | "success" | "warning"
> = {
  claimed: "default",
  prepared: "default",
  delivered: "success",
  received: "success",
  released: "warning",
};

/** The maker's Contributions with their available lifecycle actions. */
export function MyContributionsList({
  contributions,
  centers,
}: {
  contributions: MyContribution[];
  centers: CenterOption[];
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;

  if (contributions.length === 0) {
    return (
      <Card variant="transparent" className="py-12 text-center">
        <Card.Content>
          <p className="text-muted">{t.empty}</p>
        </Card.Content>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {contributions.map((c) => {
        const canSetCenter =
          c.collection_center_id === null &&
          (c.status === "claimed" || c.status === "prepared");
        return (
          <Card key={c.id}>
            <Card.Content className="flex flex-col gap-3 py-4">
              <div className="flex items-start gap-3">
                {c.resource_image_url && (
                  <Link
                    href={`/parts/${c.resource_id}?from=contributions`}
                    className="shrink-0"
                    aria-label={c.resource_name}
                  >
                    {/* External, user-supplied image URL: next/image would need
                        every host allow-listed, so a plain img is the pragmatic
                        choice here. */}
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={c.resource_image_url}
                      alt={c.resource_name}
                      className="h-16 w-16 rounded-lg object-cover"
                    />
                  </Link>
                )}
                <div className="flex flex-col gap-0.5">
                  <Link
                    href={`/parts/${c.resource_id}?from=contributions`}
                    className="font-semibold hover:underline"
                  >
                    {c.resource_name}
                  </Link>
                  <Link
                    href={`/requests/${c.request_id}?from=contributions`}
                    className="text-xs text-muted hover:underline"
                  >
                    {t.fromRequest} {c.request_title}
                  </Link>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1 text-sm">
                  <span>
                    {t.quantity}: <strong>{c.quantity}</strong>
                  </span>
                  <Chip color={STATUS_COLOR[c.status]} variant="soft" size="sm">
                    {t.status[c.status]}
                  </Chip>
                  {c.collection_center_id === null ? (
                    <span className="text-xs text-muted">{t.noCenterYet}</span>
                  ) : (
                    <Link
                      href={`/centers/${c.collection_center_id}?from=contributions`}
                      className="text-xs text-muted hover:underline"
                    >
                      {t.dropOffAt} {c.collection_center_name}
                    </Link>
                  )}
                  {c.auto_received && (
                    <span className="text-xs text-muted">{t.autoReceived}</span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {c.status === "claimed" && (
                    <ActionButton
                      id={c.id}
                      action="mark-prepared"
                      label={t.markPrinted}
                    />
                  )}
                  {c.status === "prepared" &&
                    c.collection_center_id !== null && (
                      <ActionButton
                        id={c.id}
                        action="mark-delivered"
                        label={t.markDelivered}
                      />
                    )}
                  {(c.status === "claimed" || c.status === "prepared") && (
                    <ActionButton
                      id={c.id}
                      action="release"
                      label={t.release}
                      variant="secondary"
                    />
                  )}
                </div>
              </div>

              {canSetCenter && (
                <div
                  className="border-t pt-3"
                  style={{ borderColor: "var(--card-border)" }}
                >
                  <SetCenterForm contributionId={c.id} centers={centers} />
                </div>
              )}
            </Card.Content>
          </Card>
        );
      })}
    </div>
  );
}

function ActionButton({
  id,
  action,
  label,
  variant,
}: {
  id: string;
  action: "mark-prepared" | "mark-delivered" | "release";
  label: string;
  variant?: "secondary";
}) {
  const boundAction = advanceContributionAction.bind(null, id, action, null);
  return (
    <form
      action={async () => {
        await boundAction();
      }}
    >
      <Button type="submit" size="sm" variant={variant}>
        {label}
      </Button>
    </form>
  );
}
