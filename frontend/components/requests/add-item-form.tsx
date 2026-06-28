"use client";

import {
  Alert,
  Button,
  Input,
  type Key,
  Label,
  ListBox,
  Select,
} from "@heroui/react";
import { useActionState, useState } from "react";

import { type AddItemState, addItemAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";

const initialState: AddItemState = { error: null };

/** Inline "add a part" form on the campaign detail (effective requester). */
export function AddItemForm({
  requestId,
  parts,
  existingPartIds,
}: {
  requestId: string;
  parts: Part[];
  /** Parts already on the campaign — disabled in the picker. */
  existingPartIds: string[];
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const action = addItemAction.bind(null, requestId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [partId, setPartId] = useState("");
  const taken = new Set(existingPartIds);

  if (parts.length === 0) {
    return <p className="text-sm text-muted">{t.noParts}</p>;
  }

  return (
    <form action={formAction} className="flex flex-col gap-3">
      <input type="hidden" name="part_id" value={partId} />
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 sm:max-w-md">
          <Label>{t.itemPart}</Label>
          <Select
            aria-label={t.itemPart}
            value={partId}
            onChange={(value: Key | null) =>
              setPartId(value === null ? "" : String(value))
            }
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {parts.map((part) => (
                  <ListBox.Item
                    key={part.id}
                    id={part.id}
                    textValue={part.name}
                    isDisabled={taken.has(part.id)}
                  >
                    {part.name}
                    {taken.has(part.id) ? ` · ${t.alreadyAdded}` : ""}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        <div className="w-40 shrink-0">
          <Label className="whitespace-nowrap">{t.itemQuantity}</Label>
          <Input type="number" name="quantity" min={1} />
        </div>
      </div>

      {state.error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{state.error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <Button
        type="submit"
        size="sm"
        isPending={pending}
        className="self-start"
      >
        {t.addItemSubmit}
      </Button>
    </form>
  );
}
