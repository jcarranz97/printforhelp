/** Raw API calls for the Part catalog (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type PartStatus = "active" | "discontinued";

/**
 * Demand-vs-supply signal for a Part: how many open requests still need it
 * versus how many makers are currently printing it. Drives the
 * requests-vs-claims bar in the catalog and on the detail page.
 */
export type PartStats = {
  resource_id: string;
  request_count: number;
  claim_count: number;
};

export type Part = {
  id: string;
  name: string;
  description: string | null;
  source_url: string;
  image_url: string | null;
  tags: string[];
  status: PartStatus;
  featured: boolean;
  creator_id: string;
  owner_user_id: string | null;
  owner_organization_id: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type PartFilters = {
  tag?: string;
  status?: PartStatus;
  search?: string;
};

export type CreatePartPayload = {
  name: string;
  source_url: string;
  description?: string;
  image_url?: string;
  tags?: string[];
};

export type UpdatePartPayload = {
  name?: string;
  source_url?: string;
  description?: string | null;
  image_url?: string | null;
  tags?: string[];
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** List the public Part catalog, filterable by tag/status/search (FR-021). */
export async function listParts(
  filters: PartFilters = {},
  token?: string,
): Promise<Part[]> {
  const params = new URLSearchParams();
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.status) {
    params.set("status", filters.status);
  }
  if (filters.search) {
    params.set("search", filters.search);
  }
  const query = params.toString();
  const res = await fetch(
    `${apiBaseUrl()}/resources${query ? `?${query}` : ""}`,
    {
      headers: authHeaders(token),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Part[];
}

/** Fetch a single Part by id, or null when it does not exist. */
export async function getPart(id: string): Promise<Part | null> {
  const res = await fetch(`${apiBaseUrl()}/resources/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Part;
}

/**
 * Fetch requests-vs-claims counts for every Part with any activity. Parts
 * with no requests and no claims are omitted, so callers zero-fill misses.
 */
export async function listPartStats(): Promise<PartStats[]> {
  const res = await fetch(`${apiBaseUrl()}/resources/stats`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as PartStats[];
}

/** Build a lookup of Part id -> stats, zero-filling any missing entries. */
export async function listPartStatsMap(): Promise<Record<string, PartStats>> {
  const stats = await listPartStats();
  return Object.fromEntries(stats.map((s) => [s.resource_id, s]));
}

/** Fetch requests-vs-claims counts for a single Part. */
export async function getPartStats(id: string): Promise<PartStats> {
  const res = await fetch(`${apiBaseUrl()}/resources/${id}/stats`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as PartStats;
}

/** Register a Part; the caller becomes its owner (FR-015). */
export async function createPart(
  payload: CreatePartPayload,
  token: string,
): Promise<Part> {
  const res = await fetch(`${apiBaseUrl()}/resources`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Part;
}

/** Edit a Part's mutable fields (effective owner or maintainer/admin). */
export async function updatePart(
  id: string,
  payload: UpdatePartPayload,
  token: string,
): Promise<Part> {
  const res = await fetch(`${apiBaseUrl()}/resources/${id}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Part;
}
