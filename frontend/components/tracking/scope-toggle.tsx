"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { useI18n } from "@/i18n/provider";

/**
 * Checkbox that toggles whether a group tracking page also shows the updates
 * posted on individual items. Reflected in the URL (`?items=group`) so the
 * choice is shareable and survives a reload.
 */
export function ScopeToggle({ includeItems }: { includeItems: boolean }) {
  const { dict } = useI18n();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function onToggle(next: boolean) {
    const params = new URLSearchParams(searchParams);
    if (next) {
      params.delete("items");
    } else {
      params.set("items", "group");
    }
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={includeItems}
        onChange={(event) => onToggle(event.target.checked)}
        className="h-4 w-4"
      />
      {dict.tracking.showItemUpdates}
    </label>
  );
}
