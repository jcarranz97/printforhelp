"use client";

import { Input, Label, TextField } from "@heroui/react";
import { useMemo, useState } from "react";

import { useI18n } from "@/i18n/provider";

/**
 * "Who is the project for?" — a free-text field with a typeahead over the
 * beneficiary values other projects have used, so a recurring beneficiary (a
 * hospital, a shelter) can be reused without retyping. The value is always
 * freely editable: suggestions only assist, they do not constrain. Submits the
 * `beneficiary` field.
 */
export function BeneficiaryField({
  suggestions,
  defaultValue = "",
}: {
  suggestions: string[];
  defaultValue?: string;
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const [value, setValue] = useState(defaultValue);
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => {
    const q = value.trim().toLowerCase();
    return suggestions
      .filter((s) => {
        const lower = s.toLowerCase();
        // Hide an exact match (nothing left to complete), filter by substring.
        return lower !== q && (!q || lower.includes(q));
      })
      .slice(0, 8);
  }, [suggestions, value]);

  return (
    <div className="relative">
      <TextField
        name="beneficiary"
        value={value}
        onChange={(v) => {
          setValue(v);
          setOpen(true);
        }}
      >
        <Label>{t.beneficiaryLabel}</Label>
        <Input
          placeholder={t.beneficiaryPlaceholder}
          autoComplete="off"
          onFocus={() => setOpen(true)}
          // Delay closing so a click on a suggestion registers first.
          onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        />
      </TextField>

      {open && matches.length > 0 && (
        <div className="absolute z-20 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-[var(--card-border)] bg-[var(--background)] p-1 shadow-lg">
          {matches.map((s) => (
            <button
              key={s}
              type="button"
              // onMouseDown fires before the input's onBlur, so the pick is
              // not swallowed by the blur-close above.
              onMouseDown={(e) => {
                e.preventDefault();
                setValue(s);
                setOpen(false);
              }}
              className="block w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-default-100"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
