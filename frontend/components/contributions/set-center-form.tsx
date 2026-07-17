"use client";

import { Alert, Button, type Key, Label, ListBox, Select } from "@heroui/react";
import { useActionState, useEffect, useMemo, useState } from "react";

import {
  type SetCenterState,
  setContributionCenterAction,
} from "@/actions/contributions.action";
import { useI18n } from "@/i18n/provider";

const initialState: SetCenterState = { error: null };

export type CenterOption = { id: string; name: string };

/** Inline picker to assign or change a drop-off center on a claimed/prepared
 * contribution (before delivery). When the parent request marks preferred
 * centers, the choices are restricted to those; a lone one is pre-selected. */
export function SetCenterForm({
  contributionId,
  centers,
  currentCenterId,
  preferredCenterIds = [],
  hasCenter = false,
  hideLabel = false,
}: {
  contributionId: string;
  centers: CenterOption[];
  currentCenterId?: string;
  preferredCenterIds?: string[];
  hasCenter?: boolean;
  /** Drop the visible field label (kept as the Select's aria-label) when an
   * enclosing accordion trigger already names the section. */
  hideLabel?: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.myContributions;
  const action = setContributionCenterAction.bind(null, contributionId);
  const [state, formAction, pending] = useActionState(action, initialState);
  // When the request names preferred centers, restrict the picker to them.
  const availableCenters = useMemo(() => {
    if (preferredCenterIds.length === 0) {
      return centers;
    }
    const allowed = new Set(preferredCenterIds);
    return centers.filter((c) => allowed.has(c.id));
  }, [centers, preferredCenterIds]);
  // Default: keep the current center, else pre-select the lone available one.
  const [centerId, setCenterId] = useState(
    () =>
      currentCenterId ??
      (availableCenters.length === 1 ? availableCenters[0].id : ""),
  );
  const [editing, setEditing] = useState(false);
  const [justUpdated, setJustUpdated] = useState(false);

  // After a successful change, collapse the picker and flag the update so the
  // maker sees it landed while still being able to change it again.
  useEffect(() => {
    if (state.success) {
      setEditing(false);
      setJustUpdated(true);
    }
  }, [state]);

  if (availableCenters.length === 0) {
    return <p className="text-xs text-muted">{t.noCentersYet}</p>;
  }

  // Once a center is assigned, keep the card compact: collapse to a small
  // prompt and only reveal the picker when the maker wants to change it.
  if (hasCenter && !editing) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        {justUpdated && (
          <span className="text-xs font-medium text-[var(--accent-strong)]">
            ✓ {t.centerUpdated}
          </span>
        )}
        <button
          type="button"
          onClick={() => {
            setJustUpdated(false);
            setEditing(true);
          }}
          className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
        >
          {t.changeCenterPrompt}
        </button>
      </div>
    );
  }

  return (
    <form action={formAction} className="flex flex-wrap items-end gap-2">
      <input type="hidden" name="collection_center_id" value={centerId} />
      <div className="min-w-44 flex-1">
        {!hideLabel && <Label className="text-xs">{t.setCenterLabel}</Label>}
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
              {availableCenters.map((center) => (
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
        {hasCenter ? t.changeCenter : t.setCenter}
      </Button>
      {hasCenter && (
        <button
          type="button"
          onClick={() => {
            setCenterId(currentCenterId ?? "");
            setEditing(false);
          }}
          className="text-xs text-muted hover:underline"
        >
          {t.cancel}
        </button>
      )}
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
