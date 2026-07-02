/** Shared helpers for choosing a Resource (part or supply) on a request. */

import type { Part } from "@/lib/parts.api";
import type { Supply } from "@/lib/supplies.api";

export type ResourceKind = "part" | "supply";

/** A catalog entry reduced to what a request item picker needs. */
export type ResourceOption = {
  id: string;
  name: string;
  kind: ResourceKind;
  /** Suggested units for a supply (empty for parts). */
  units: string[];
};

/** Combine the parts and supplies catalogs into a single option list. */
export function toResourceOptions(
  parts: Part[],
  supplies: Supply[],
): ResourceOption[] {
  return [
    ...parts.map((p) => ({
      id: p.id,
      name: p.name,
      kind: "part" as const,
      units: [],
    })),
    ...supplies.map((s) => ({
      id: s.id,
      name: s.name,
      kind: "supply" as const,
      units: s.units,
    })),
  ];
}

/** Map of resource id → display name, for labelling items on a request. */
export function resourceNameMap(
  parts: Part[],
  supplies: Supply[],
): Record<string, string> {
  const map: Record<string, string> = {};
  for (const p of parts) {
    map[p.id] = p.name;
  }
  for (const s of supplies) {
    map[s.id] = s.name;
  }
  return map;
}
