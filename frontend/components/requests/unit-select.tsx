"use client";

import { useId, useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";

/**
 * A single-value, creatable unit picker (tag-input style). The typed text is
 * the value; a dropdown suggests the resource's known units as you type and
 * offers a "Create <x>" affordance for a brand-new one. Controlled by the
 * parent (which owns the value and mirrors it into the submitted form data).
 */
export function UnitSelect({
  label,
  value,
  onChange,
  suggestions,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  suggestions: string[];
}) {
  const { dict, locale } = useI18n();
  const t = dict.tagInput;
  const inputId = useId();
  const [open, setOpen] = useState(false);

  const sorted = useMemo(
    () =>
      [...suggestions].sort((a, b) =>
        a.localeCompare(b, locale, { sensitivity: "base" }),
      ),
    [suggestions, locale],
  );

  const query = value.trim().toLowerCase();
  const matches = sorted.filter((u) => u.toLowerCase().includes(query));
  // Offer "Create" only when the typed value matches no known unit exactly.
  const canCreate =
    query.length > 0 && !suggestions.some((u) => u.toLowerCase() === query);

  function pick(unit: string) {
    onChange(unit);
    setOpen(false);
  }

  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={inputId} className="text-sm font-medium text-foreground">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          value={value}
          onChange={(event) => {
            onChange(event.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              setOpen(false);
            } else if (event.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={dict.requestForm.itemUnitPlaceholder}
          className="w-full rounded-lg border border-[var(--card-border)] bg-transparent px-2 py-1.5 text-sm outline-none"
        />

        {open && (matches.length > 0 || canCreate) && (
          <ul className="absolute z-10 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-[var(--card-border)] bg-[var(--card)] py-1 shadow-lg">
            {matches.map((unit) => (
              <li key={unit}>
                {/* onMouseDown keeps the input from blurring before the click. */}
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => pick(unit)}
                  className="block w-full px-3 py-1.5 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10"
                >
                  {unit}
                </button>
              </li>
            ))}
            {canCreate && (
              <li>
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => pick(value.trim())}
                  className="block w-full px-3 py-1.5 text-left text-sm font-medium text-[var(--accent-strong)] hover:bg-black/5 dark:hover:bg-white/10"
                >
                  {t.createLabel} “{value.trim()}”
                </button>
              </li>
            )}
          </ul>
        )}
      </div>
    </div>
  );
}
