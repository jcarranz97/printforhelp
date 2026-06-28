/** Raw API calls for the collection centers directory (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type CollectionCenterStatus = "active" | "inactive";

export type CollectionCenter = {
  id: string;
  name: string;
  address: string;
  country: string;
  city: string;
  contact: string;
  opening_hours: string | null;
  notes: string | null;
  verified: boolean;
  registered_by_id: string;
  verified_by_id: string | null;
  owner_user_id: string | null;
  owner_organization_id: string | null;
  status: CollectionCenterStatus;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type CollectionCenterFilters = {
  country?: string;
  city?: string;
  /** Maintainer/admin filter, e.g. `false` for the unverified queue. */
  verified?: boolean;
};

export type CreateCollectionCenterPayload = {
  name: string;
  address: string;
  country: string;
  city: string;
  contact: string;
  opening_hours?: string;
  notes?: string;
};

export type UpdateCollectionCenterPayload = {
  name?: string;
  address?: string;
  country?: string;
  city?: string;
  contact?: string;
  opening_hours?: string | null;
  notes?: string | null;
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * List collection centers (FR-072). With no token this is the public
 * directory (every operational center, verified or not). A maintainer
 * token plus `verified` filters the list (e.g. the unverified queue).
 */
export async function listCollectionCenters(
  filters: CollectionCenterFilters = {},
  token?: string,
): Promise<CollectionCenter[]> {
  const params = new URLSearchParams();
  if (filters.country) {
    params.set("country", filters.country);
  }
  if (filters.city) {
    params.set("city", filters.city);
  }
  if (filters.verified !== undefined) {
    params.set("verified", String(filters.verified));
  }
  const query = params.toString();
  const url = `${apiBaseUrl()}/collection-centers${query ? `?${query}` : ""}`;

  const res = await fetch(url, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter[];
}

/**
 * Fetch a single collection center by id. Returns null when the center
 * is not found or not visible to the caller. A token lets effective
 * members and maintainers see their own inactive / archived centers.
 */
export async function getCollectionCenter(
  id: string,
  token?: string,
): Promise<CollectionCenter | null> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/${id}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Register a new collection center. The endpoint is open: with a token the
 * center is owned by the caller; without one it is submitted anonymously
 * (owned by the system account). Either way it starts `verified = false`
 * (FR-083 / FR-027).
 */
export async function createCollectionCenter(
  payload: CreateCollectionCenterPayload,
  token?: string,
): Promise<CollectionCenter> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Edit a center's mutable fields (FR-031). Requires a token: the backend
 * authorizes effective members (owner, contributors, owning-org members)
 * and maintainers/admins. Only the provided fields are changed.
 */
export async function updateCollectionCenter(
  id: string,
  payload: UpdateCollectionCenterPayload,
  token: string,
): Promise<CollectionCenter> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/${id}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Whether the token holder may manage a center (its shipments, etc.).
 * The contributors endpoint requires effective membership, so a `200`
 * means the caller is an owner, contributor, owning-org member, or a
 * maintainer/admin; anything else means "cannot manage" (FR-129).
 */
export async function canManageCenter(
  id: string,
  token?: string,
): Promise<boolean> {
  if (!token) {
    return false;
  }
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${id}/contributors`,
    { headers: authHeaders(token), cache: "no-store" },
  );
  return res.ok;
}

/** Verify a collection center (maintainer/admin, FR-027). */
export async function verifyCollectionCenter(
  token: string,
  id: string,
): Promise<CollectionCenter> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/${id}/verify`, {
    method: "POST",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/** Revoke a collection center's verification (maintainer/admin). */
export async function revokeCollectionCenterVerification(
  token: string,
  id: string,
  reason?: string,
): Promise<CollectionCenter> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${id}/revoke-verification`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ reason: reason ?? null }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}
