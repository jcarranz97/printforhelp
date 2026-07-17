"use client";

import { Alert, Button } from "@heroui/react";
import Link from "next/link";
import { useMemo, useState, useTransition } from "react";

import { setItemCentersAction } from "@/actions/requests.action";
import { useI18n } from "@/i18n/provider";

export type ItemCenter = {
  id: string;
  name: string;
  city: string;
  country: string;
  location_url: string | null;
};

/** Resolve the item's effective centers: its subset of the request's preferred
 * list, or all of them when the item names none. */
function effectiveIds(candidateIds: string[], selectedIds: string[]): string[] {
  const allowed = new Set(candidateIds);
  const filtered = selectedIds.filter((id) => allowed.has(id));
  return filtered.length > 0 ? filtered : candidateIds;
}

/**
 * The drop-off centers where this item's help is needed. Everyone sees the
 * effective list (name, city, and a location link) so they can judge whether a
 * center is near them. The requester can narrow the request's preferred centers
 * to just the ones this specific item needs.
 */
export function ItemPreferredCenters({
  requestId,
  itemId,
  candidates,
  selectedIds,
  canManage,
  hideHeading = false,
}: {
  requestId: string;
  itemId: string;
  /** The request's preferred centers (the full candidate set). */
  candidates: ItemCenter[];
  /** The item's stored subset (empty = all candidates apply). */
  selectedIds: string[];
  canManage: boolean;
  /** Drop the section title (e.g. when the label is already the accordion
   * trigger); the "edit centers" control still shows, right-aligned. */
  hideHeading?: boolean;
}) {
  const { dict } = useI18n();
  const t = dict.requestItem;
  const candidateIds = useMemo(() => candidates.map((c) => c.id), [candidates]);

  const [checked, setChecked] = useState<Set<string>>(
    () => new Set(effectiveIds(candidateIds, selectedIds)),
  );
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  if (candidates.length === 0) {
    return null;
  }

  const effective = new Set(effectiveIds(candidateIds, selectedIds));
  const activeCenters = candidates.filter((c) => effective.has(c.id));

  function toggle(id: string, on: boolean) {
    setChecked((prev) => {
      const next = new Set(prev);
      if (on) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }

  function save() {
    setError(null);
    startTransition(async () => {
      const result = await setItemCentersAction(
        requestId,
        itemId,
        Array.from(checked),
      );
      if (result.error) {
        setError(result.error);
        return;
      }
      setSaved(true);
      setEditing(false);
    });
  }

  return (
    <section className="flex flex-col gap-3">
      {(!hideHeading || (canManage && !editing)) && (
        <div
          className={`flex flex-wrap items-center gap-2 ${
            hideHeading ? "justify-end" : "justify-between"
          }`}
        >
          {!hideHeading && (
            <h2 className="text-lg font-semibold text-foreground">
              {t.centersHeading}
            </h2>
          )}
          {canManage && !editing && (
            <button
              type="button"
              onClick={() => {
                setSaved(false);
                setChecked(new Set(effectiveIds(candidateIds, selectedIds)));
                setEditing(true);
              }}
              className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
            >
              {t.centersEdit}
            </button>
          )}
        </div>
      )}
      <p className="text-xs text-muted">{t.centersHelp}</p>

      {!editing && (
        <ul className="flex flex-col gap-2">
          {activeCenters.map((center) => (
            <li
              key={center.id}
              className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-[var(--card-border)] px-3 py-2 text-sm"
            >
              <Link
                href={`/centers/${center.id}?from=item`}
                className="font-medium hover:underline"
              >
                {center.name}
                <span className="ml-2 text-xs text-muted">
                  {center.city}, {center.country}
                </span>
              </Link>
              {center.location_url && (
                <a
                  href={center.location_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs font-medium text-[var(--accent-strong)] hover:underline"
                >
                  {t.centersDirections}
                  <span aria-hidden="true"> ↗</span>
                </a>
              )}
            </li>
          ))}
        </ul>
      )}

      {canManage && editing && (
        <div className="flex flex-col gap-3 rounded-xl border border-[var(--card-border)] p-3">
          <p className="text-xs text-muted">{t.centersEditHint}</p>
          <div className="flex flex-col gap-1.5">
            {candidates.map((center) => (
              <label
                key={center.id}
                className="flex items-center gap-2 text-sm"
              >
                <input
                  type="checkbox"
                  checked={checked.has(center.id)}
                  onChange={(event) => toggle(center.id, event.target.checked)}
                  className="h-4 w-4"
                />
                {center.name}
                <span className="text-xs text-muted">
                  {center.city}, {center.country}
                </span>
              </label>
            ))}
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
            <Button type="button" size="sm" onPress={save} isPending={pending}>
              {t.centersSave}
            </Button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="text-xs text-muted hover:underline"
            >
              {t.centersCancel}
            </button>
          </div>
        </div>
      )}

      {saved && !editing && (
        <span className="text-xs font-medium text-[var(--accent-strong)]">
          ✓ {t.centersSaved}
        </span>
      )}
    </section>
  );
}
