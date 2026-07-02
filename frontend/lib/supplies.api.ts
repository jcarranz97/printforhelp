/** Raw API calls for the Supplies catalog (server-side only).
 *
 * A "supply" (ES "insumo") is a non-printed aid item — a `Resource` with
 * `category = "other"`. It shares the `/resources` endpoint with parts; the
 * category both scopes reads and is sent on create so parts and supplies stay
 * in separate catalogs with no schema change.
 */

import { apiBaseUrl, toApiError } from "@/lib/api";

/** The single generic category every v1 supply uses. */
export const SUPPLY_CATEGORY = "other";

export type SupplyStatus = "active" | "discontinued";

export type Supply = {
  id: string;
  name: string;
  description: string | null;
  /** Optional reference link (unlike parts, not required for supplies). */
  source_url: string | null;
  image_url: string | null;
  /** Suggested units of measure (e.g. "litros", "cajas"); empty = pieces. */
  units: string[];
  tags: string[];
  status: SupplyStatus;
  featured: boolean;
  creator_id: string;
  owner_user_id: string | null;
  owner_organization_id: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type SupplyFilters = {
  tag?: string;
  status?: SupplyStatus;
  search?: string;
};

export type CreateSupplyPayload = {
  name: string;
  description?: string;
  image_url?: string;
  units?: string[];
  tags?: string[];
};

export type UpdateSupplyPayload = {
  name?: string;
  description?: string | null;
  image_url?: string | null;
  units?: string[];
  tags?: string[];
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** List the public Supplies catalog, filterable by tag/status/search. */
export async function listSupplies(
  filters: SupplyFilters = {},
  token?: string,
): Promise<Supply[]> {
  const params = new URLSearchParams();
  params.set("category", SUPPLY_CATEGORY);
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  const res = await fetch(`${apiBaseUrl()}/resources?${params.toString()}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Supply[];
}

/** Fetch a single Supply by id, or null when it does not exist. */
export async function getSupply(id: string): Promise<Supply | null> {
  const res = await fetch(`${apiBaseUrl()}/resources/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Supply;
}

/** Register a Supply; the caller becomes its owner (FR-015). */
export async function createSupply(
  payload: CreateSupplyPayload,
  token: string,
): Promise<Supply> {
  const res = await fetch(`${apiBaseUrl()}/resources`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ ...payload, category: SUPPLY_CATEGORY }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Supply;
}

/** Edit a Supply's mutable fields (effective owner or maintainer/admin). */
export async function updateSupply(
  id: string,
  payload: UpdateSupplyPayload,
  token: string,
): Promise<Supply> {
  const res = await fetch(`${apiBaseUrl()}/resources/${id}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Supply;
}
