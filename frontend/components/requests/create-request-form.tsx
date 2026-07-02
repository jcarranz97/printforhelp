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
  TextField,
} from "@heroui/react";
import { useActionState, useMemo, useState } from "react";

import {
  type CreateRequestState,
  createRequestAction,
} from "@/actions/requests.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { PreferredCentersField } from "@/components/requests/preferred-centers-field";
import { UnitSelect } from "@/components/requests/unit-select";
import { useI18n } from "@/i18n/provider";
import type { CenterOption } from "@/components/requests/preferred-centers-field";
import type { ResourceKind, ResourceOption } from "@/lib/resource-options";

const initialState: CreateRequestState = { error: null };

type ItemRow = {
  key: number;
  resourceId: string;
  quantity: string;
  unit: string;
};
type KindFilter = "both" | ResourceKind;

/**
 * Create-campaign form with dynamic item rows. A kind filter scopes every
 * row's picker to parts, supplies, or both; each row picks a Resource and an
 * optional target quantity. The rows are serialized into a hidden `items`
 * JSON field the server action parses. Optional preferred drop-off centers
 * are serialized into `preferred_center_ids`.
 */
export function CreateRequestForm({
  resources,
  centers,
}: {
  resources: ResourceOption[];
  centers: CenterOption[];
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const [state, formAction, pending] = useActionState(
    createRequestAction,
    initialState,
  );
  const [kind, setKind] = useState<KindFilter>("both");
  const [rows, setRows] = useState<ItemRow[]>([
    { key: 0, resourceId: "", quantity: "", unit: "" },
  ]);

  const resourceById = useMemo(() => {
    const map = new Map<string, ResourceOption>();
    for (const r of resources) {
      map.set(r.id, r);
    }
    return map;
  }, [resources]);

  const visibleResources = useMemo(
    () => resources.filter((r) => kind === "both" || r.kind === kind),
    [resources, kind],
  );

  function addRow() {
    setRows((prev) => [
      ...prev,
      {
        key: (prev.at(-1)?.key ?? 0) + 1,
        resourceId: "",
        quantity: "",
        unit: "",
      },
    ]);
  }

  function removeRow(key: number) {
    setRows((prev) =>
      prev.length > 1 ? prev.filter((r) => r.key !== key) : prev,
    );
  }

  function setResource(key: number, value: Key | null) {
    const nextId = value === null ? "" : String(value);
    const resource = resourceById.get(nextId);
    // Seed the unit from the supply's first suggestion; clear it for parts.
    const nextUnit =
      resource?.kind === "supply" ? (resource.units[0] ?? "") : "";
    setRows((prev) =>
      prev.map((r) =>
        r.key === key ? { ...r, resourceId: nextId, unit: nextUnit } : r,
      ),
    );
  }

  function setQuantity(key: number, value: string) {
    setRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, quantity: value } : r)),
    );
  }

  function setUnit(key: number, value: string) {
    setRows((prev) =>
      prev.map((r) => (r.key === key ? { ...r, unit: value } : r)),
    );
  }

  function onKindChange(value: Key | null) {
    const next = (value === null ? "both" : String(value)) as KindFilter;
    setKind(next);
    // Clear any row whose selection the new filter would hide.
    setRows((prev) =>
      prev.map((r) =>
        resources.some(
          (res) =>
            res.id === r.resourceId && (next === "both" || res.kind === next),
        )
          ? r
          : { ...r, resourceId: "", unit: "" },
      ),
    );
  }

  const itemsJson = JSON.stringify(
    rows
      .filter((r) => r.resourceId)
      .map((r) => ({
        resource_id: r.resourceId,
        quantity: r.quantity ? Number(r.quantity) : null,
        // Units apply only to supplies; parts stay countable pieces.
        unit:
          resourceById.get(r.resourceId)?.kind === "supply"
            ? r.unit.trim() || null
            : null,
      })),
  );

  // Resources already chosen in some row — disabled in the other rows' pickers
  // so the same one can't be added twice (the backend also rejects it).
  const chosenIds = new Set(rows.map((r) => r.resourceId).filter(Boolean));

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

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={3}
              placeholder={t.descriptionPlaceholder}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.imageUpload}</span>
            <input
              type="file"
              name="image_file"
              accept="image/png,image/jpeg,image/webp"
              className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-default-100 file:px-3 file:py-1.5 file:text-sm file:font-medium"
            />
            <span className="text-xs text-muted">{t.imageUploadHint}</span>
          </div>

          <TextField name="image_url" type="url">
            <Label>{t.imageUrl}</Label>
            <Input placeholder={t.imageUrlPlaceholder} />
          </TextField>

          <TextField name="deadline" type="date">
            <Label>{t.deadline}</Label>
            <Input />
          </TextField>

          <PreferredCentersField centers={centers} />

          <fieldset className="flex flex-col gap-3">
            <legend className="text-sm font-medium">{t.itemsHeading}</legend>
            <p className="text-xs text-muted">
              {resources.length > 0 ? t.itemsHint : t.noParts}
            </p>

            {resources.length > 0 && (
              <div className="w-full sm:w-44">
                <Label>{t.itemKind}</Label>
                <Select
                  aria-label={t.itemKind}
                  value={kind}
                  onChange={onKindChange}
                >
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
            )}

            {resources.length > 0 &&
              rows.map((row) => (
                <div key={row.key} className="flex flex-wrap items-end gap-3">
                  <div className="min-w-48 flex-1">
                    <Label>{t.itemResource}</Label>
                    <Select
                      aria-label={t.itemResource}
                      value={row.resourceId}
                      onChange={(value) => setResource(row.key, value)}
                    >
                      <Select.Trigger>
                        <Select.Value />
                        <Select.Indicator />
                      </Select.Trigger>
                      <Select.Popover>
                        <ListBox>
                          {visibleResources.map((resource) => (
                            <ListBox.Item
                              key={resource.id}
                              id={resource.id}
                              textValue={resource.name}
                              isDisabled={
                                chosenIds.has(resource.id) &&
                                resource.id !== row.resourceId
                              }
                            >
                              {resource.name}
                              {chosenIds.has(resource.id) &&
                              resource.id !== row.resourceId
                                ? ` · ${t.alreadyAdded}`
                                : ""}
                              <ListBox.ItemIndicator />
                            </ListBox.Item>
                          ))}
                        </ListBox>
                      </Select.Popover>
                    </Select>
                  </div>
                  <div className="w-32">
                    <TextField
                      type="number"
                      value={row.quantity}
                      onChange={(value) => setQuantity(row.key, value)}
                    >
                      <Label>{t.itemQuantity}</Label>
                      <Input type="number" min={1} />
                    </TextField>
                  </div>
                  {resourceById.get(row.resourceId)?.kind === "supply" && (
                    <div className="w-36">
                      <UnitSelect
                        label={t.itemUnit}
                        value={row.unit}
                        onChange={(value) => setUnit(row.key, value)}
                        suggestions={
                          resourceById.get(row.resourceId)?.units ?? []
                        }
                      />
                    </div>
                  )}
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
            {resources.length > 0 && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="self-start"
                onPress={addRow}
              >
                {t.addItem}
              </Button>
            )}
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
