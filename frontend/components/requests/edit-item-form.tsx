"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type UpdateItemState,
  updateItemAction,
} from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { RequestItem } from "@/lib/requests.api";

const initialState: UpdateItemState = { error: null };

/** Inline "edit target" control for a campaign item (effective requester). */
export function EditItemForm({
  requestId,
  item,
}: {
  requestId: string;
  item: RequestItem;
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const action = updateItemAction.bind(null, requestId, item.id);
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <form action={formAction} className="flex flex-wrap items-end gap-3">
      <div className="w-32">
        <TextField
          name="quantity"
          type="number"
          defaultValue={item.quantity != null ? String(item.quantity) : ""}
        >
          <Label>{t.editTargetLabel}</Label>
          <Input type="number" min={1} placeholder={t.openEnded} />
        </TextField>
      </div>
      <Button type="submit" size="sm" variant="secondary" isPending={pending}>
        {t.saveTarget}
      </Button>
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
