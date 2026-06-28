"use client";

import { Button, Card, Chip } from "@heroui/react";

import { advanceContributionAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";
import type { Contribution, ContributionStatus } from "@/lib/contributions.api";

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
}: {
  contributions: Contribution[];
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
      {contributions.map((c) => (
        <Card key={c.id}>
          <Card.Content className="flex flex-wrap items-center justify-between gap-4 py-4">
            <div className="flex flex-col gap-1 text-sm">
              <span>
                {t.quantity}: <strong>{c.quantity}</strong>
              </span>
              <Chip color={STATUS_COLOR[c.status]} variant="soft" size="sm">
                {t.status[c.status]}
              </Chip>
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
              {c.status === "printed" && (
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
          </Card.Content>
        </Card>
      ))}
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
