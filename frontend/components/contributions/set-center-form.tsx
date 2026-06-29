"use client";

import { Alert, Button, type Key, Label, ListBox, Select } from "@heroui/react";
import { useActionState, useState } from "react";

import {
  type SetCenterState,
  setContributionCenterAction,
} from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: SetCenterState = { error: null };

export type CenterOption = { id: string; name: string };

/** Inline picker to assign a drop-off center to a claimed/prepared print. */
export function SetCenterForm({
  contributionId,
  centers,
}: {
  contributionId: string;
  centers: CenterOption[];
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const action = setContributionCenterAction.bind(null, contributionId);
  const [state, formAction, pending] = useActionState(action, initialState);
  const [centerId, setCenterId] = useState("");

  if (centers.length === 0) {
    return <p className="text-xs text-muted">{t.noCentersYet}</p>;
  }

  return (
    <form action={formAction} className="flex flex-wrap items-end gap-2">
      <input type="hidden" name="collection_center_id" value={centerId} />
      <div className="min-w-44 flex-1">
        <Label className="text-xs">{t.setCenterLabel}</Label>
        <Select
          aria-label={t.setCenterLabel}
          value={centerId}
          onChange={(value: Key | null) =>
            setCenterId(value === null ? "" : String(value))
          }
        >
          <Select.Trigger>
            <Select.Value />
            <Select.Indicator />
          </Select.Trigger>
          <Select.Popover>
            <ListBox>
              {centers.map((center) => (
                <ListBox.Item
                  key={center.id}
                  id={center.id}
                  textValue={center.name}
                >
                  {center.name}
                  <ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
      </div>
      <Button type="submit" size="sm" variant="secondary" isPending={pending}>
        {t.setCenter}
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
