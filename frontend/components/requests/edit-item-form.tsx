"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState, useState } from "react";

import {
  type UpdateItemState,
  updateItemAction,
} from "@/actions/requests.action";
import { UnitSelect } from "@/components/requests/unit-select";
import { useI18n } from "@/i18n/provider";
import type { RequestItem } from "@/lib/requests.api";

const initialState: UpdateItemState = { error: null };

/** Inline "edit target" control for a campaign item (effective requester).
 * For supply items it also lets the requester pick/change the unit. */
export function EditItemForm({
  requestId,
  item,
  isSupply = false,
  unitSuggestions = [],
}: {
  requestId: string;
  item: RequestItem;
  isSupply?: boolean;
  unitSuggestions?: string[];
}) {
  const { dict } = useI18n();
  const t = dict.requestDetail;
  const action = updateItemAction.bind(null, requestId, item.id);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [unit, setUnit] = useState(item.unit ?? "");

  return (
    <form action={formAction} className="flex flex-wrap items-end gap-3">
      {isSupply && <input type="hidden" name="unit" value={unit} />}
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
      {isSupply && (
        <div className="w-36">
          <UnitSelect
            label={dict.requestForm.itemUnit}
            value={unit}
            onChange={setUnit}
            suggestions={unitSuggestions}
          />
        </div>
      )}
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
