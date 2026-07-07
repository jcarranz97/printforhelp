"use client";

import {
  Alert,
  Button,
  Input,
  type Key,
  Label,
  ListBox,
  Select,
  TextField,
} from "@heroui/react";
import { useActionState, useState } from "react";

import { type AddItemState, addItemAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { ResourceOption } from "@/lib/resource-options";

const initialState: AddItemState = { error: null };

/** Inline "add a 3D part" form on the campaign detail (effective requester). */
export function AddItemForm({
  requestId,
  resources,
}: {
  requestId: string;
  resources: ResourceOption[];
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const action = addItemAction.bind(null, requestId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [resourceId, setResourceId] = useState("");

  if (resources.length === 0) {
    return <p className="text-sm text-muted">{t.noParts}</p>;
  }

  function onResourceChange(value: Key | null) {
    setResourceId(value === null ? "" : String(value));
  }

  return (
    <form action={formAction} className="flex flex-col gap-3">
      <input type="hidden" name="resource_id" value={resourceId} />
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-0 flex-1 sm:max-w-md">
          <Label>{t.itemResource}</Label>
          <Select
            aria-label={t.itemResource}
            value={resourceId}
            onChange={onResourceChange}
          >
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                {resources.map((resource) => (
                  <ListBox.Item
                    key={resource.id}
                    id={resource.id}
                    textValue={resource.name}
                  >
                    {resource.name}
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
        <div className="w-32 shrink-0">
          <TextField name="quantity" type="number">
            <Label className="whitespace-nowrap">{t.itemQuantity}</Label>
            <Input type="number" min={1} />
          </TextField>
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
