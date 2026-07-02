"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useState, useTransition } from "react";

import { createPrivateCenterAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";

export type CenterOption = {
  id: string;
  name: string;
  /** False = a private, request-specific drop-off location. */
  listed?: boolean;
};

const EMPTY_LOCATION = {
  name: "",
  address: "",
  country: "",
  city: "",
  contact: "",
  location_url: "",
  opening_hours: "",
};

/**
 * Optional preferred drop-off centers for a request. Checkboxes over public
 * verified centers plus the requester's own private locations, and an inline
 * form to add a new private (unlisted) location. The selected UUIDs serialize
 * into a single hidden `preferred_center_ids` field the server action parses.
 * Private locations stay out of the public directory but are shown to helpers
 * on the request/item pages and in "My Contributions".
 */
export function PreferredCentersField({
  centers,
  defaultSelectedIds = [],
}: {
  centers: CenterOption[];
  defaultSelectedIds?: string[];
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const [candidates, setCandidates] = useState<CenterOption[]>(centers);
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(defaultSelectedIds),
  );
  const [adding, setAdding] = useState(false);
  const [location, setLocation] = useState(EMPTY_LOCATION);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  function toggle(id: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  function setField(field: keyof typeof EMPTY_LOCATION, value: string) {
    setLocation((prev) => ({ ...prev, [field]: value }));
  }

  function addLocation() {
    setError(null);
    startTransition(async () => {
      const result = await createPrivateCenterAction(location);
      if (result.error || !result.center) {
        setError(result.error ?? t.errorGeneric);
        return;
      }
      const c = result.center;
      setCandidates((prev) => [
        ...prev,
        { id: c.id, name: c.name, listed: false },
      ]);
      setSelected((prev) => new Set(prev).add(c.id));
      setLocation(EMPTY_LOCATION);
      setAdding(false);
    });
  }

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{t.preferredCenters}</legend>
      <p className="text-xs text-muted">{t.preferredCentersHint}</p>
      <input
        type="hidden"
        name="preferred_center_ids"
        value={Array.from(selected).join(",")}
      />

      {candidates.length === 0 ? (
        <p className="text-xs text-muted">{t.preferredCentersEmpty}</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {candidates.map((center) => (
            <label key={center.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.has(center.id)}
                onChange={(event) => toggle(center.id, event.target.checked)}
                className="h-4 w-4"
              />
              {center.name}
              {center.listed === false && (
                <span className="rounded-full bg-default-100 px-2 py-0.5 text-xs text-muted">
                  {t.privateCenterTag}
                </span>
              )}
            </label>
          ))}
        </div>
      )}

      {adding ? (
        <div className="mt-1 flex flex-col gap-2 rounded-xl border border-[var(--card-border)] p-3">
          <p className="text-xs text-muted">{t.addLocationHint}</p>
          <div className="grid gap-2 sm:grid-cols-2">
            <TextField
              value={location.name}
              onChange={(v) => setField("name", v)}
            >
              <Label className="text-xs">{t.locationName}</Label>
              <Input />
            </TextField>
            <TextField
              value={location.contact}
              onChange={(v) => setField("contact", v)}
            >
              <Label className="text-xs">{t.locationContact}</Label>
              <Input />
            </TextField>
            <TextField
              value={location.address}
              onChange={(v) => setField("address", v)}
              className="sm:col-span-2"
            >
              <Label className="text-xs">{t.locationAddress}</Label>
              <Input />
            </TextField>
            <TextField
              value={location.city}
              onChange={(v) => setField("city", v)}
            >
              <Label className="text-xs">{t.locationCity}</Label>
              <Input />
            </TextField>
            <TextField
              value={location.country}
              onChange={(v) => setField("country", v)}
            >
              <Label className="text-xs">{t.locationCountry}</Label>
              <Input />
            </TextField>
            <TextField
              type="url"
              value={location.location_url}
              onChange={(v) => setField("location_url", v)}
            >
              <Label className="text-xs">{t.locationMapUrl}</Label>
              <Input type="url" placeholder="https://maps…" />
            </TextField>
            <TextField
              value={location.opening_hours}
              onChange={(v) => setField("opening_hours", v)}
            >
              <Label className="text-xs">{t.locationHours}</Label>
              <Input />
            </TextField>
          </div>
          {error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
          <div className="flex items-center gap-3">
            <Button
              type="button"
              size="sm"
              onPress={addLocation}
              isPending={pending}
            >
              {t.addLocationSubmit}
            </Button>
            <button
              type="button"
              onClick={() => {
                setAdding(false);
                setError(null);
              }}
              className="text-xs text-muted hover:underline"
            >
              {t.cancel}
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="self-start text-xs font-medium text-[var(--accent-strong)] hover:underline"
        >
          {t.addLocation}
        </button>
      )}
    </fieldset>
  );
}
