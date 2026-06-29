"use client";

import { Button, Card, Chip } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";

import {
  closeItemAction,
  closeRequestAction,
  removeItemAction,
} from "@/actions/requests.action";
import { Markdown } from "@/components/comments/markdown";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";
import type { RequestDetail, RequestItem } from "@/lib/requests.api";

import { AddItemForm } from "./add-item-form";
import { ClaimForm, type CenterOption } from "./claim-form";
import { EditItemForm } from "./edit-item-form";

/** Campaign detail: per-item progress, the claim flow, and item management. */
export function RequestDetailView({
  request,
  parts,
  partNames,
  centers,
  isLoggedIn,
  canManage,
}: {
  request: RequestDetail;
  parts: Part[];
  partNames: Record<string, string>;
  centers: CenterOption[];
  isLoggedIn: boolean;
  canManage: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const statusT = dict.requests.status;
  const closeAction = closeRequestAction.bind(null, request.id);
  const isOpen = request.status === "open";

  return (
    <div className="flex flex-col gap-8">
      {request.image_url && (
        // External/stored cover image: a plain img avoids next/image host
        // allow-listing, matching the catalog cards.
        <img
          src={request.image_url}
          alt={request.title}
          className="max-h-72 w-full rounded-2xl object-cover"
        />
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{request.title}</h1>
            <Chip variant="soft" size="sm">
              {statusT[request.status]}
            </Chip>
          </div>
          {request.description && (
            <div className="mt-3 max-w-2xl">
              <Markdown source={request.description} />
            </div>
          )}
          <p className="mt-3 text-sm text-muted">
            {t.deadline}: {request.deadline ?? t.noDeadline}
          </p>
        </div>
        {canManage && isOpen && (
          <div className="flex gap-2">
            <Link
              href={`/requests/${request.id}/edit`}
              className={buttonVariants({ size: "sm", variant: "secondary" })}
            >
              {t.edit}
            </Link>
            <form
              action={async () => {
                await closeAction();
              }}
            >
              <Button type="submit" variant="secondary" size="sm">
                {t.close}
              </Button>
            </form>
          </div>
        )}
      </div>

      <section className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t.itemsHeading}</h2>
        {request.items.map((item) => (
          <ItemCard
            key={item.id}
            requestId={request.id}
            item={item}
            partName={partNames[item.resource_id] ?? item.resource_id}
            centers={centers}
            isLoggedIn={isLoggedIn}
            canManage={canManage && isOpen}
            canRemove={
              canManage &&
              isOpen &&
              item.status === "open" &&
              item.progress.committed_quantity === 0 &&
              request.items.length > 1
            }
          />
        ))}

        {canManage && isOpen && (
          <Card>
            <Card.Header>
              <Card.Title>{t.addPartHeading}</Card.Title>
            </Card.Header>
            <Card.Content>
              <AddItemForm
                requestId={request.id}
                parts={parts}
                existingPartIds={request.items.map((i) => i.resource_id)}
              />
            </Card.Content>
          </Card>
        )}
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
  canManage,
  canRemove,
}: {
  requestId: string;
  item: RequestItem;
  partName: string;
  centers: CenterOption[];
  isLoggedIn: boolean;
  canManage: boolean;
  canRemove: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const claimT = dict.claim;
  const p = item.progress;
  const target = p.target_quantity;
  const pct = (value: number) =>
    target && target > 0 ? Math.min(100, (value / target) * 100) : 0;
  const closeItem = closeItemAction.bind(null, requestId, item.id);
  const removeItem = removeItemAction.bind(null, requestId, item.id);

  return (
    <Card>
      <Card.Header>
        <div className="flex items-center justify-between gap-3">
          <Card.Title>{partName}</Card.Title>
          <div className="flex items-center gap-2">
            {item.status !== "open" && (
              <Chip variant="soft" size="sm" color="warning">
                {item.status === "fulfilled" ? t.itemFulfilled : t.itemClosed}
              </Chip>
            )}
            {canManage && item.status === "open" && (
              <form
                action={async () => {
                  await closeItem();
                }}
              >
                <Button type="submit" variant="secondary" size="sm">
                  {t.closeItem}
                </Button>
              </form>
            )}
            {canRemove && (
              <form
                action={async () => {
                  await removeItem();
                }}
              >
                <Button type="submit" variant="secondary" size="sm">
                  {t.removeItem}
                </Button>
              </form>
            )}
          </div>
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

        {canManage && item.status === "open" && (
          <div
            className="mt-2 border-t pt-3"
            style={{ borderColor: "var(--card-border)" }}
          >
            <EditItemForm requestId={requestId} item={item} />
          </div>
        )}

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
