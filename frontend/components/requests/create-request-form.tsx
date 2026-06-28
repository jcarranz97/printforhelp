"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  type Key,
  Label,
  ListBox,
  Select,
  TextArea,
  TextField,
} from "@heroui/react";
import { useActionState, useState } from "react";

import {
  type CreateRequestState,
  createRequestAction,
} from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";

const initialState: CreateRequestState = { error: null };

type ItemRow = { key: number; partId: string; quantity: string };

/**
 * Create-campaign form with dynamic item rows. Each row picks a Part and
 * an optional target quantity; the rows are serialized into a hidden
 * `items` JSON field the server action parses.
 */
export function CreateRequestForm({ parts }: { parts: Part[] }) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const [state, formAction, pending] = useActionState(
    createRequestAction,
    initialState,
  );
  const [rows, setRows] = useState<ItemRow[]>([
    { key: 0, partId: "", quantity: "" },
  ]);

  function addRow() {
    setRows((prev) => [
      ...prev,
      { key: (prev.at(-1)?.key ?? 0) + 1, partId: "", quantity: "" },
    ]);
  }

  function removeRow(key: number) {
    setRows((prev) =>
      prev.length > 1 ? prev.filter((r) => r.key !== key) : prev,
    );
  }

  function setPart(key: number, value: Key | null) {
    setRows((prev) =>
      prev.map((r) =>
        r.key === key
          ? { ...r, partId: value === null ? "" : String(value) }
          : r,
      ),
    );
  }

  function setQuantity(key: number, value: string) {
    setRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, quantity: value } : r)),
    );
  }

  const itemsJson = JSON.stringify(
    rows
      .filter((r) => r.partId)
      .map((r) => ({
        part_id: r.partId,
        quantity: r.quantity ? Number(r.quantity) : null,
      })),
  );

  if (parts.length === 0) {
    return (
      <Card>
        <Card.Content className="py-8 text-center text-muted">
          {t.noParts}
        </Card.Content>
      </Card>
    );
  }

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.title}</Card.Title>
        <Card.Description>{t.description}</Card.Description>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-col gap-4">
          <TextField name="title" type="text" isRequired>
            <Label>{t.campaignTitle}</Label>
            <Input placeholder={t.campaignTitlePlaceholder} />
          </TextField>

          <TextField name="description">
            <Label>{t.descriptionLabel}</Label>
            <TextArea rows={2} placeholder={t.descriptionPlaceholder} />
          </TextField>

          <TextField name="deadline" type="date">
            <Label>{t.deadline}</Label>
            <Input />
          </TextField>

          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium">{t.itemsHeading}</legend>
            {rows.map((row) => (
              <div key={row.key} className="flex flex-wrap items-end gap-3">
                <div className="min-w-48 flex-1">
                  <Label>{t.itemPart}</Label>
                  <Select
                    aria-label={t.itemPart}
                    value={row.partId}
                    onChange={(value) => setPart(row.key, value)}
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
                          >
                            {part.name}
                            <ListBox.ItemIndicator />
                          </ListBox.Item>
                        ))}
                      </ListBox>
                    </Select.Popover>
                  </Select>
                </div>
                <div className="w-32">
                  <Label>{t.itemQuantity}</Label>
                  <Input
                    type="number"
                    min={1}
                    value={row.quantity}
                    onChange={(event) =>
                      setQuantity(row.key, event.target.value)
                    }
                  />
                </div>
                {rows.length > 1 && (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onPress={() => removeRow(row.key)}
                  >
                    {t.removeItem}
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="self-start"
              onPress={addRow}
            >
              {t.addItem}
            </Button>
          </fieldset>

          <input type="hidden" name="items" value={itemsJson} />

          {state.error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{state.error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <Button type="submit" isPending={pending} className="self-start">
            {t.submit}
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
