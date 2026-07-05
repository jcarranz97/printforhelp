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
import { useActionState, useMemo, useState } from "react";

import { type AddItemState, addItemAction } from "@/actions/requests.action";
import { UnitSelect } from "@/components/requests/unit-select";
import { useI18n } from "@/i18n/provider";
import type { ResourceKind, ResourceOption } from "@/lib/resource-options";

const initialState: AddItemState = { error: null };

type KindFilter = "both" | ResourceKind;

/** Inline "add an item" form on the campaign detail (effective requester). */
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
  const [kind, setKind] = useState<KindFilter>("both");
  const [resourceId, setResourceId] = useState("");
  const [unit, setUnit] = useState("");

  const visible = useMemo(
    () => resources.filter((r) => kind === "both" || r.kind === kind),
    [resources, kind],
  );

  const selected = resources.find((r) => r.id === resourceId);
  const isSupply = selected?.kind === "supply";

  if (resources.length === 0) {
    return <p className="text-sm text-muted">{t.noParts}</p>;
  }

  function onResourceChange(value: Key | null) {
    const next = value === null ? "" : String(value);
    setResourceId(next);
    // Seed the unit from the supply's first suggestion; clear for parts.
    const resource = resources.find((r) => r.id === next);
    setUnit(resource?.kind === "supply" ? (resource.units[0] ?? "") : "");
  }

  function onKindChange(value: Key | null) {
    const next = (value === null ? "both" : String(value)) as KindFilter;
    setKind(next);
    // Drop the current selection (and its unit) if the new filter hides it.
    const stillVisible = resources.some(
      (r) => r.id === resourceId && (next === "both" || r.kind === next),
    );
    if (!stillVisible) {
      setResourceId("");
      setUnit("");
    }
  }

  return (
    <form action={formAction} className="flex flex-col gap-3">
      <input type="hidden" name="resource_id" value={resourceId} />
      <input type="hidden" name="unit" value={isSupply ? unit : ""} />
      <div className="flex flex-wrap items-end gap-3">
        <div className="w-full sm:w-44">
          <Label>{t.itemKind}</Label>
          <Select aria-label={t.itemKind} value={kind} onChange={onKindChange}>
            <Select.Trigger>
              <Select.Value />
              <Select.Indicator />
            </Select.Trigger>
            <Select.Popover>
              <ListBox>
                <ListBox.Item id="both" textValue={t.itemKindBoth}>
                  {t.itemKindBoth}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                <ListBox.Item id="part" textValue={t.itemKindParts}>
                  {t.itemKindParts}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
                <ListBox.Item id="supply" textValue={t.itemKindSupplies}>
                  {t.itemKindSupplies}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              </ListBox>
            </Select.Popover>
          </Select>
        </div>
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
                {visible.map((resource) => (
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
        {isSupply && (
          <div className="w-36 shrink-0">
            <UnitSelect
              label={t.itemUnit}
              value={unit}
              onChange={setUnit}
              suggestions={selected?.units ?? []}
            />
          </div>
        )}
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
