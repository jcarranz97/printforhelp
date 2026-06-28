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
  printed: "default",
  delivered: "success",
  received: "success",
  released: "warning",
};

/** The maker's Contributions with their available lifecycle actions. */
export function MyPrintsList({
  contributions,
  centers,
}: {
  contributions: MyContribution[];
  centers: CenterOption[];
}) {
  const { dict } = useI18n();
  const t = dict.myPrints;

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
          (c.status === "claimed" || c.status === "printed");
        return (
          <Card key={c.id}>
            <Card.Content className="flex flex-col gap-3 py-4">
              <div className="flex flex-col gap-0.5">
                <Link
                  href={`/parts/${c.part_id}`}
                  className="font-semibold hover:underline"
                >
                  {c.part_name}
                </Link>
                <Link
                  href={`/requests/${c.request_id}`}
                  className="text-xs text-muted hover:underline"
                >
                  {t.fromRequest} {c.request_title}
                </Link>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex flex-col gap-1 text-sm">
                  <span>
                    {t.quantity}: <strong>{c.quantity}</strong>
                  </span>
                  <Chip color={STATUS_COLOR[c.status]} variant="soft" size="sm">
                    {t.status[c.status]}
                  </Chip>
                  {c.collection_center_id === null && (
                    <span className="text-xs text-muted">{t.noCenterYet}</span>
                  )}
                  {c.auto_received && (
                    <span className="text-xs text-muted">{t.autoReceived}</span>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {c.status === "claimed" && (
                    <ActionButton
                      id={c.id}
                      action="mark-printed"
                      label={t.markPrinted}
                    />
                  )}
                  {c.status === "printed" &&
                    c.collection_center_id !== null && (
                      <ActionButton
                        id={c.id}
                        action="mark-delivered"
                        label={t.markDelivered}
                      />
                    )}
                  {(c.status === "claimed" || c.status === "printed") && (
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
  action: "mark-printed" | "mark-delivered" | "release";
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
