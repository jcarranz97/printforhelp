"use client";

import { Alert, Button, Input, TextField } from "@heroui/react";
import { useActionState, useEffect, useState } from "react";

import {
  type SetQuantityState,
  setContributionQuantityAction,
} from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: SetQuantityState = { error: null };

/** Inline "resize my commitment" control on a claimed/prepared contribution
 * (FR-057). Makers often find mid-print that they can manage more — or fewer —
 * units than they first committed to, so the amount stays editable until the
 * units are delivered. When QRs have already been generated, the maker is told
 * they reconcile automatically (already-printed labels keep working). */
export function EditQuantityForm({
  contributionId,
  quantity,
  unit,
  requestId,
  itemNumber,
  canEdit,
  hasTracking = false,
}: {
  contributionId: string;
  quantity: number;
  unit: string | null;
  requestId: string;
  itemNumber: number;
  canEdit: boolean;
  hasTracking?: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const action = setContributionQuantityAction.bind(null, contributionId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [editing, setEditing] = useState(false);
  const [justUpdated, setJustUpdated] = useState(false);

  // Collapse on success and flag it, so the maker sees the change landed and
  // can still adjust again.
  useEffect(() => {
    if (state.success) {
      setEditing(false);
      setJustUpdated(true);
    }
  }, [state]);

  const amount = (
    <span>
      {t.quantity}:{" "}
      <strong>
        {quantity}
        {unit ? ` ${unit}` : ""}
      </strong>
    </span>
  );

  if (!canEdit) {
    return amount;
  }

  if (!editing) {
    return (
      <span className="flex flex-wrap items-center gap-2">
        {amount}
        {justUpdated && (
          <span className="text-xs font-medium text-[var(--accent-strong)]">
            ✓ {t.quantityUpdated}
          </span>
        )}
        <button
          type="button"
          onClick={() => {
            setJustUpdated(false);
            setEditing(true);
          }}
          className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
        >
          {t.changeQuantityPrompt}
        </button>
      </span>
    );
  }

  return (
    <form action={formAction} className="flex flex-wrap items-end gap-2">
      <input type="hidden" name="request_id" value={requestId} />
      <input type="hidden" name="item_number" value={itemNumber} />
      <div className="w-28">
        <TextField
          name="quantity"
          type="number"
          defaultValue={String(quantity)}
          aria-label={t.quantity}
        >
          <Input type="number" min={1} autoFocus />
        </TextField>
      </div>
      <Button type="submit" size="sm" variant="secondary" isPending={pending}>
        {t.saveQuantity}
      </Button>
      <button
        type="button"
        onClick={() => setEditing(false)}
        className="text-xs text-muted hover:underline"
      >
        {t.cancel}
      </button>
      {hasTracking && (
        <p className="w-full text-xs text-muted">{t.quantityTrackingHint}</p>
      )}
      {state.error && (
        <Alert status="danger" className="w-full">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{state.error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}
    </form>
  );
}
