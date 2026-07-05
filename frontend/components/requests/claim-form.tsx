"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type ClaimState, claimAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: ClaimState = { error: null };

/**
 * Inline "I'll print this" form for a single open RequestItem. Submits a
 * Contribution (claim) for the given quantity. The drop-off center is chosen
 * later from "My Contributions" (makers rarely know it at commit time), so it
 * is not asked for here.
 */
export function ClaimForm({
  requestId,
  requestItemId,
  itemNumber,
  itemClosed = false,
}: {
  requestId: string;
  /** The item's UUID — the Contribution is created against this. */
  requestItemId: string;
  /** The item's per-request number — used to revalidate its page. */
  itemNumber: number;
  /** The item/campaign is completed or closed: still commit-able, but note it. */
  itemClosed?: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.claim;
  const [state, formAction, pending] = useActionState(
    claimAction,
    initialState,
  );

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

      <form action={formAction} className="flex flex-col gap-3">
        <input type="hidden" name="request_item_id" value={requestItemId} />
        <input type="hidden" name="request_id" value={requestId} />
        <input type="hidden" name="item_number" value={itemNumber} />

        <div className="w-28">
          <TextField name="quantity" type="number" isRequired defaultValue="1">
            <Label>{t.quantity}</Label>
            <Input type="number" min={1} />
          </TextField>
        </div>
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
          <Alert status="success">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{t.success}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}

        <Button
          type="submit"
          isPending={pending}
          className="self-start"
          size="sm"
        >
          {t.submit}
        </Button>
      </form>
    </div>
  );
}
