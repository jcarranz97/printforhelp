"use client";

import { Button, Card, Chip } from "@heroui/react";

import { closeRequestAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { RequestDetail, RequestItem } from "@/lib/requests.api";

import { ClaimForm, type CenterOption } from "./claim-form";

/** Campaign detail: per-item progress summary plus the claim flow. */
export function RequestDetailView({
  request,
  partNames,
  centers,
  isLoggedIn,
  canClose,
}: {
  request: RequestDetail;
  partNames: Record<string, string>;
  centers: CenterOption[];
  isLoggedIn: boolean;
  canClose: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const statusT = dict.requests.status;
  const closeAction = closeRequestAction.bind(null, request.id);

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{request.title}</h1>
            <Chip variant="soft" size="sm">
              {statusT[request.status]}
            </Chip>
          </div>
          {request.description && (
            <p className="mt-2 max-w-2xl text-sm text-muted">
              {request.description}
            </p>
          )}
          <p className="mt-2 text-sm text-muted">
            {t.deadline}: {request.deadline ?? t.noDeadline}
          </p>
        </div>
        {canClose && request.status === "open" && (
          <form
            action={async () => {
              await closeAction();
            }}
          >
            <Button type="submit" variant="secondary" size="sm">
              {t.close}
            </Button>
          </form>
        )}
      </div>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t.itemsHeading}</h2>
        {request.items.map((item) => (
          <ItemCard
            key={item.id}
            requestId={request.id}
            item={item}
            partName={partNames[item.part_id] ?? item.part_id}
            centers={centers}
            isLoggedIn={isLoggedIn}
          />
        ))}
      </section>
    </div>
  );
}

function ItemCard({
  requestId,
  item,
  partName,
  centers,
  isLoggedIn,
}: {
  requestId: string;
  item: RequestItem;
  partName: string;
  centers: CenterOption[];
  isLoggedIn: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const claimT = dict.claim;
  const p = item.progress;
  const target = p.target_quantity;
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;

  return (
    <Card>
      <Card.Header>
        <div className="flex items-center justify-between gap-3">
          <Card.Title>{partName}</Card.Title>
          {item.status !== "open" && (
            <Chip variant="soft" size="sm" color="warning">
              {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
            </Chip>
          )}
        </div>
        <Card.Description>
          {t.target}: {target ?? t.openEnded}
        </Card.Description>
      </Card.Header>
      <Card.Content className="flex flex-col gap-3 text-sm">
        {target ? (
          <div
            className="flex h-2 w-full overflow-hidden rounded-full"
            style={{ background: "var(--card-border)" }}
          >
            <div
              style={{
                width: `${pct(p.at_center_quantity)}%`,
                background: "var(--accent-strong)",
              }}
            />
            <div
              style={{
                width: `${pct(p.claimed_quantity)}%`,
                background: "var(--accent)",
              }}
            />
          </div>
        ) : null}
        <div className="flex flex-wrap gap-4">
          <span>
            {t.progressClaimed}: <strong>{p.claimed_quantity}</strong>
          </span>
          <span>
            {t.progressAtCenter}: <strong>{p.at_center_quantity}</strong>
          </span>
          {p.remaining !== null && (
            <span>
              {t.progressRemaining}: <strong>{p.remaining}</strong>
            </span>
          )}
        </div>

        {item.status === "open" &&
          (isLoggedIn ? (
            <ClaimForm
              requestId={requestId}
              requestItemId={item.id}
              centers={centers}
            />
          ) : (
            <p className="text-muted">{claimT.loginToClaim}</p>
          ))}
      </Card.Content>
    </Card>
  );
}
