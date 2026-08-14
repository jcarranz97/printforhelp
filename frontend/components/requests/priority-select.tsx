"use client";

import { type Key, Label, ListBox, Select } from "@heroui/react";

import { useI18n } from "@/i18n/provider";
import type { ItemPriority } from "@/lib/requests.api";

const PRIORITIES: ItemPriority[] = ["high", "medium", "low"];

/**
 * Priority picker for an item form. Controlled by the parent, which mirrors the
 * value into a hidden input — HeroUI's Select is React-Aria based, so the value
 * does not reach FormData on its own.
 */
export function PrioritySelect({
  value,
  onChange,
}: {
  value: ItemPriority;
  onChange: (value: ItemPriority) => void;
}) {
  const { dict } = useI18n();
  const label = dict.requestForm.itemPriority;
  const names = dict.requestItem.priorityFilters;

  function onSelect(key: Key | null) {
    if (key !== null) {
      onChange(String(key) as ItemPriority);
    }
  }

  return (
    <>
      <Label>{label}</Label>
      <Select aria-label={label} value={value} onChange={onSelect}>
        <Select.Trigger>
          <Select.Value />
          <Select.Indicator />
        </Select.Trigger>
        <Select.Popover>
          <ListBox>
            {PRIORITIES.map((priority) => (
              <ListBox.Item
                key={priority}
                id={priority}
                textValue={names[priority]}
              >
                {names[priority]}
                <ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
        </Select.Popover>
      </Select>
    </>
  );
}
