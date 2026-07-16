"use client";

import { Alert, Button } from "@heroui/react";
import Link from "next/link";
import { useActionState, useState } from "react";

import { type ClaimState, claimAction } from "@/actions/contributions.action";
import { SourceLinkButton } from "@/components/resources/source-link-button";
import { useI18n } from "@/i18n/provider";

const initialState: ClaimState = { error: null };

/**
 * A friendly default commitment: ~10% of what's still needed, rounded to the
 * nearest multiple of 5 (so it reads "10" or "15", never "11" or "16"), never
 * 0 and never more than what's left. Open-ended items (no target) default to 1.
 */
export function defaultClaimQuantity(remaining: number | null): number {
  if (remaining == null || remaining <= 0) {
    return 1;
  }
  const rounded = Math.round((remaining * 0.1) / 5) * 5;
  return Math.min(remaining, Math.max(5, rounded));
}

/**
 * Inline "I'll print this" form for a single open RequestItem (design 2b —
 * "Goal-driven + social proof"). A large quantity stepper, a one-tap
 * "cover what's left" button, a live projection of where the target would land
 * with the maker's pledge, and a social-proof cue. Submits a Contribution
 * (claim) for the given quantity; the drop-off center is chosen later from
 * "My Contributions" (makers rarely know it at commit time).
 */
export function ClaimForm({
  requestId,
  requestItemId,
  itemNumber,
  itemClosed = false,
  sourceUrl,
  remaining,
  committed,
  target,
  contributorCount,
}: {
  requestId: string;
  /** The item's UUID — the Contribution is created against this. */
  requestItemId: string;
  /** The item's per-request number — used to revalidate its page. */
  itemNumber: number;
  /** The item/campaign is completed or closed: still commit-able, but note it. */
  itemClosed?: boolean;
  /** Resource's source/download URL, offered right after a successful commit. */
  sourceUrl?: string;
  /** Units still needed to hit target; null for open-ended items. */
  remaining: number | null;
  /** Units already committed (claimed + at center). */
  committed: number;
  /** Target quantity; null for open-ended items. */
  target: number | null;
  /** Distinct makers already committed (drives the social-proof pill). */
  contributorCount: number;
}) {
  const { dict } = useI18n();
  const t = dict.claim;
  const [state, formAction, pending] = useActionState(
    claimAction,
    initialState,
  );
  const [qty, setQty] = useState(() => defaultClaimQuantity(remaining));
  const setQtySafe = (value: number) =>
    setQty(Math.max(1, Math.floor(value) || 1));

  const hasTarget = target != null && target > 0;
  const clampPct = (value: number) =>
    hasTarget ? Math.min(100, (value / target) * 100) : 0;
  const projected = committed + Math.max(0, qty);
  const projPct = Math.round(clampPct(projected));
  const projLeft = hasTarget ? Math.max(0, target - projected) : 0;
  const canFillRemaining = remaining != null && remaining > 0;

  return (
    <div
      className="mt-2 border-t pt-4"
      style={{ borderColor: "var(--card-border)" }}
    >
      <h3 className="text-sm font-semibold">{t.heading}</h3>
      {itemClosed ? (
        <p className="mb-3 text-xs text-muted">{t.stillHelpNote}</p>
      ) : (
        <p className="mb-3 text-xs text-muted">{t.subtitle}</p>
      )}

      {/* Social proof: only shown once a couple of makers are already in, so
      the count always reads as plural and the cue actually feels motivating. */}
      {contributorCount >= 2 && (
        <div
          className="mb-4 flex w-fit items-center gap-2.5 rounded-full py-1.5 pl-1.5 pr-3.5"
          style={{
            background: "color-mix(in srgb, var(--muted) 12%, transparent)",
          }}
        >
          <div className="flex" aria-hidden="true">
            {["var(--accent-strong)", "#12a594", "var(--accent)"].map(
              (color, i) => (
                <span
                  key={color}
                  className="h-[26px] w-[26px] rounded-full border-2"
                  style={{
                    background: color,
                    borderColor: "var(--card)",
                    marginLeft: i === 0 ? 0 : "-9px",
                  }}
                />
              ),
            )}
          </div>
          <span className="text-[12.5px]" style={{ color: "var(--muted)" }}>
            {t.socialProofJoin}{" "}
            <strong style={{ color: "var(--accent-strong)" }}>
              {contributorCount} {t.socialProofPeople}
            </strong>{" "}
            {t.socialProofSuffix}
          </span>
        </div>
      )}

      <form action={formAction} className="flex flex-col gap-4">
        <input type="hidden" name="request_item_id" value={requestItemId} />
        <input type="hidden" name="request_id" value={requestId} />
        <input type="hidden" name="item_number" value={itemNumber} />

        <div>
          <label
            htmlFor={`qty-${requestItemId}`}
            className="mb-2 block text-xs font-semibold uppercase tracking-wide"
            style={{ color: "var(--muted)" }}
          >
            {t.quantity}
          </label>
          <div className="flex items-center justify-center gap-3.5">
            <button
              type="button"
              onClick={() => setQtySafe(qty - 1)}
              aria-label={t.decrease}
              className="flex h-12 w-12 items-center justify-center rounded-2xl border text-2xl leading-none"
              style={{
                borderColor: "var(--card-border)",
                color: "var(--accent-strong)",
              }}
            >
              −
            </button>
            <input
              id={`qty-${requestItemId}`}
              name="quantity"
              type="number"
              min={1}
              value={qty}
              onChange={(e) => setQtySafe(Number(e.target.value))}
              className="h-14 w-24 rounded-2xl border text-center text-2xl font-extrabold"
              style={{
                borderColor: "var(--card-border)",
                color: "var(--foreground)",
                background: "var(--card)",
              }}
            />
            <button
              type="button"
              onClick={() => setQtySafe(qty + 1)}
              aria-label={t.increase}
              className="flex h-12 w-12 items-center justify-center rounded-2xl border text-2xl leading-none"
              style={{
                borderColor: "var(--card-border)",
                color: "var(--accent-strong)",
              }}
            >
              +
            </button>
          </div>
        </div>

        {canFillRemaining && (
          <button
            type="button"
            onClick={() => setQtySafe(remaining)}
            className="w-full rounded-xl border border-dashed py-2.5 text-sm font-bold"
            style={{
              borderColor: "var(--accent-strong)",
              color: "var(--accent-strong)",
              background:
                "color-mix(in srgb, var(--accent-strong) 6%, transparent)",
            }}
          >
            {t.fillRemaining} ({remaining})
          </button>
        )}

        {/* Live projection: where the campaign lands if this pledge goes
        through. Solid = already committed, striped = the maker's added pledge. */}
        {hasTarget && (
          <div>
            <div
              className="relative h-2.5 overflow-hidden rounded-full"
              style={{ background: "var(--card-border)" }}
            >
              <div
                className="absolute inset-y-0 left-0 transition-[width] duration-300"
                style={{
                  width: `${clampPct(projected)}%`,
                  backgroundImage:
                    "repeating-linear-gradient(45deg, var(--accent) 0 6px, var(--accent-strong) 6px 12px)",
                }}
              />
              <div
                className="absolute inset-y-0 left-0 transition-[width] duration-300"
                style={{
                  width: `${clampPct(committed)}%`,
                  background: "var(--accent-strong)",
                }}
              />
            </div>
            <p
              className="mt-2 text-center text-[13px]"
              style={{ color: "var(--muted)" }}
            >
              {t.projectionPre}{" "}
              <strong style={{ color: "var(--accent-strong)" }}>
                {projPct}%
              </strong>{" "}
              {t.projectionMid}{" "}
              <strong style={{ color: "var(--foreground)" }}>{projLeft}</strong>
            </p>
          </div>
        )}

        <p className="text-xs text-muted">{t.centerLater}</p>

        {state.error && (
          <Alert status="danger">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{state.error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
        {state.success && (
          <>
            <Alert status="success">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>
                  {t.success}{" "}
                  <Link
                    href="/my-contributions"
                    className="font-medium underline"
                  >
                    {t.successLink}
                  </Link>
                  .
                </Alert.Description>
              </Alert.Content>
            </Alert>
            {sourceUrl && (
              // Nudge the maker straight to the file/link while momentum is
              // high — right after they commit is when they go to print.
              <div
                className="flex flex-col gap-2 rounded-lg border px-3 py-3"
                style={{
                  borderColor: "var(--accent-strong)",
                  background:
                    "color-mix(in srgb, var(--accent-strong) 8%, transparent)",
                }}
              >
                <p className="text-sm font-medium">{t.thanksReady}</p>
                <div>
                  <SourceLinkButton url={sourceUrl} />
                </div>
              </div>
            )}
          </>
        )}

        <Button type="submit" isPending={pending} className="w-full">
          {t.submit}
        </Button>
      </form>
    </div>
  );
}
