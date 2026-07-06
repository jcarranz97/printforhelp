"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useMemo, useState, useTransition } from "react";

import { createPrivateCenterAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";

export type CenterOption = {
  id: string;
  name: string;
  city: string;
  country: string;
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

/** "City, COUNTRY" (either part optional), e.g. "Maracaibo, VE". */
function formatPlace(center: CenterOption): string {
  return [center.city, center.country?.toUpperCase()]
    .filter(Boolean)
    .join(", ");
}

/**
 * Preferred drop-off centers for a request. Type to search the directory (by
 * name, city, or country) and pick a match; each pick drops into a checkbox
 * list **below** the search box. The list holds only the centers picked from
 * search — not the whole directory — and each row can be checked/unchecked to
 * include or exclude it (or removed with its ✕). If a center is missing, an
 * inline form registers a new private (unlisted) location and adds it to the
 * list. Only the *checked* rows serialize into the hidden `preferred_center_ids`
 * field the server action parses.
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
  // `picked` = rows shown below the search box (order preserved); `checked` =
  // which of those are actually included. An unchecked row stays in the list so
  // it can be re-checked without searching again.
  const initialPicked = useMemo(
    () => defaultSelectedIds.filter((id) => centers.some((c) => c.id === id)),
    [defaultSelectedIds, centers],
  );
  const [picked, setPicked] = useState<string[]>(initialPicked);
  const [checked, setChecked] = useState<Set<string>>(
    () => new Set(initialPicked),
  );
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [location, setLocation] = useState(EMPTY_LOCATION);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const byId = useMemo(
    () => new Map(candidates.map((c) => [c.id, c])),
    [candidates],
  );

  // Directory matches not already in the list below, ranked by the typed query.
  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    return candidates.filter((c) => {
      if (picked.includes(c.id)) {
        return false;
      }
      if (!q) {
        return true;
      }
      return (
        c.name.toLowerCase().includes(q) ||
        c.city.toLowerCase().includes(q) ||
        c.country.toLowerCase().includes(q)
      );
    });
  }, [candidates, picked, query]);

  // Add a center from search: append to the list (if new) and check it.
  function pick(id: string) {
    setPicked((prev) => (prev.includes(id) ? prev : [...prev, id]));
    setChecked((prev) => new Set(prev).add(id));
    setQuery("");
    setOpen(false);
  }

  function toggle(id: string, isChecked: boolean) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (isChecked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  // Drop a row from the list entirely (the ✕).
  function removeRow(id: string) {
    setPicked((prev) => prev.filter((x) => x !== id));
    setChecked((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });
  }

  function setField(field: keyof typeof EMPTY_LOCATION, value: string) {
    setLocation((prev) => ({ ...prev, [field]: value }));
  }

  function openAddForm() {
    // Seed the new location's name with whatever the user was searching for.
    setLocation({ ...EMPTY_LOCATION, name: query.trim() });
    setError(null);
    setAdding(true);
    setOpen(false);
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
      const option: CenterOption = {
        id: c.id,
        name: c.name,
        city: c.city,
        country: c.country,
        listed: false,
      };
      setCandidates((prev) => [...prev, option]);
      setPicked((prev) => (prev.includes(c.id) ? prev : [...prev, c.id]));
      setChecked((prev) => new Set(prev).add(c.id));
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
        value={Array.from(checked).join(",")}
      />

      {/* Search box + autocomplete dropdown. */}
      {!adding && (
        <div className="relative">
          <TextField
            aria-label={t.preferredCenters}
            value={query}
            onChange={(v) => {
              setQuery(v);
              setOpen(true);
            }}
          >
            <Input
              placeholder={t.centersSearchPlaceholder}
              onFocus={() => setOpen(true)}
              // Delay closing so a click on an option registers first.
              onBlur={() => window.setTimeout(() => setOpen(false), 120)}
            />
          </TextField>

          {open && (
            <div className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-xl border border-[var(--card-border)] bg-[var(--background)] p-1 shadow-lg">
              {matches.length > 0 ? (
                matches.map((center) => {
                  const place = formatPlace(center);
                  return (
                    <button
                      key={center.id}
                      type="button"
                      // onMouseDown fires before the input's onBlur, so the
                      // pick is not swallowed by the blur-close above.
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pick(center.id);
                      }}
                      className="flex w-full flex-col items-start rounded-lg px-3 py-2 text-left text-sm hover:bg-default-100"
                    >
                      <span className="flex items-center gap-2">
                        {center.name}
                        {center.listed === false && (
                          <span className="rounded-full bg-default-100 px-2 py-0.5 text-[10px] uppercase text-muted">
                            {t.privateCenterTag}
                          </span>
                        )}
                      </span>
                      {place && (
                        <span className="text-xs text-muted">{place}</span>
                      )}
                    </button>
                  );
                })
              ) : (
                <p className="px-3 py-2 text-xs text-muted">
                  {t.centersNoMatches}
                </p>
              )}
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  openAddForm();
                }}
                className="mt-1 flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-medium text-[var(--accent-strong)] hover:bg-default-100"
              >
                {t.addLocation}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Picked centers — a checkbox list below the search, each toggleable. */}
      {picked.length > 0 && (
        <div className="flex flex-col gap-1.5">
          {picked.map((id) => {
            const center = byId.get(id);
            if (!center) {
              return null;
            }
            const place = formatPlace(center);
            return (
              <div key={id} className="flex items-center gap-2 text-sm">
                <label className="flex flex-1 items-center gap-2">
                  <input
                    type="checkbox"
                    checked={checked.has(id)}
                    onChange={(e) => toggle(id, e.target.checked)}
                    className="h-4 w-4"
                  />
                  <span>
                    {center.name}
                    {place && <span className="text-muted"> · {place}</span>}
                  </span>
                  {center.listed === false && (
                    <span className="rounded-full bg-default-100 px-2 py-0.5 text-[10px] uppercase text-muted">
                      {t.privateCenterTag}
                    </span>
                  )}
                </label>
                <button
                  type="button"
                  onClick={() => removeRow(id)}
                  aria-label={t.centersRemove}
                  className="flex h-5 w-5 items-center justify-center rounded-full text-muted hover:bg-default-200 hover:text-foreground"
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      )}

      {/* Inline "add a private location" form. */}
      {adding && (
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
      )}
    </fieldset>
  );
}
