"use client";

import {
  Alert,
  Button,
  Input,
  type Key,
  Label,
  ListBox,
  Select,
  TextArea,
  TextField,
} from "@heroui/react";
import { useActionState, useState } from "react";

import { type ClaimState, claimAction } from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: ClaimState = { error: null };

export type CenterOption = { id: string; name: string };

/**
 * Inline "I'll print this" form for a single open RequestItem. Submits a
 * Contribution (claim) at the chosen verified center.
 */
export function ClaimForm({
  requestId,
  requestItemId,
  centers,
}: {
  requestId: string;
  requestItemId: string;
  centers: CenterOption[];
}) {
  const { dict } = useI18n();
  const t = dict.claim;
  const [state, formAction, pending] = useActionState(
    claimAction,
    initialState,
  );
  const [centerId, setCenterId] = useState("");

  if (centers.length === 0) {
    return <p className="text-sm text-muted">{t.noCenters}</p>;
  }

  return (
    <form action={formAction} className="flex flex-col gap-3">
      <input type="hidden" name="request_item_id" value={requestItemId} />
      <input type="hidden" name="request_id" value={requestId} />
      <input type="hidden" name="collection_center_id" value={centerId} />

      <div className="flex flex-wrap items-end gap-3">
        <div className="w-28">
          <TextField name="quantity" type="number" isRequired>
            <Label>{t.quantity}</Label>
            <Input type="number" min={1} defaultValue="1" />
          </TextField>
        </div>
        <div className="min-w-48 flex-1">
          <Label>{t.center}</Label>
          <Select
            aria-label={t.center}
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
      </div>

      <TextField name="notes">
        <Label>{t.notes}</Label>
        <TextArea rows={2} placeholder={t.notesPlaceholder} />
      </TextField>

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
  );
}
