"use client";

import { useState } from "react";

import { useI18n } from "@/i18n/provider";

export type CenterOption = { id: string; name: string };

/**
 * Optional preferred drop-off centers for a request. Renders a checkbox list
 * and serializes the selected center UUIDs into a single hidden
 * `preferred_center_ids` field (comma-separated) the server action parses.
 * When set, makers see only these centers in "My Contributions".
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
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(defaultSelectedIds),
  );

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

  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-sm font-medium">{t.preferredCenters}</legend>
      <p className="text-xs text-muted">{t.preferredCentersHint}</p>
      <input
        type="hidden"
        name="preferred_center_ids"
        value={Array.from(selected).join(",")}
      />
      {centers.length === 0 ? (
        <p className="text-xs text-muted">{t.preferredCentersEmpty}</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {centers.map((center) => (
            <label key={center.id} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={selected.has(center.id)}
                onChange={(event) => toggle(center.id, event.target.checked)}
                className="h-4 w-4"
              />
              {center.name}
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}
