/** Raw API calls for the collection centers directory (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type CollectionCenterStatus = "active" | "inactive";

/** One per-centre contributor row (matches the backend ContributorResponse). */
export type CenterContributor = {
  id: string;
  collection_center_id: string;
  user_id: string;
  username: string;
  full_name: string | null;
  avatar_url: string | null;
  avatar_crop_x: number;
  avatar_crop_y: number;
  avatar_crop_w: number;
  avatar_crop_h: number;
  role: string;
};

export type CollectionCenter = {
  id: string;
  name: string;
  address: string;
  country: string;
  state: string | null;
  city: string;
  contact: string;
  location_url: string | null;
  opening_hours: string | null;
  description: string | null;
  tags: string[];
  /** False = a private, request-specific drop-off (hidden from the directory). */
  listed: boolean;
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
  /** State/province exact match (e.g. `CA`). */
  state?: string;
  city?: string;
  /** Tag exact match (center must carry this tag). */
  tag?: string;
  /** Maintainer/admin filter, e.g. `false` for the unverified queue. */
  verified?: boolean;
  /**
   * Maintainer/admin filter. Pass `false` to list archived (soft-deleted)
   * centers — the restore queue. Ignored for everyone else.
   */
  active?: boolean;
};

export type CreateCollectionCenterPayload = {
  name: string;
  address: string;
  country: string;
  state: string;
  city: string;
  contact: string;
  location_url?: string;
  opening_hours?: string;
  description?: string;
  tags?: string[];
  /** Set false to register a private, request-specific drop-off location. */
  listed?: boolean;
  owner_organization_id?: string;
};

export type UpdateCollectionCenterPayload = {
  name?: string;
  address?: string;
  country?: string;
  state?: string | null;
  city?: string;
  contact?: string;
  location_url?: string | null;
  opening_hours?: string | null;
  description?: string | null;
  tags?: string[];
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
  if (filters.state) {
    params.set("state", filters.state);
  }
  if (filters.city) {
    params.set("city", filters.city);
  }
  if (filters.tag) {
    params.set("tag", filters.tag);
  }
  if (filters.verified !== undefined) {
    params.set("verified", String(filters.verified));
  }
  if (filters.active !== undefined) {
    params.set("active", String(filters.active));
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
 * List the caller's own centers (listed + unlisted), for drop-off pickers.
 * Covers centers owned by the caller or an org they belong to, so a requester
 * can reuse their private, request-specific locations across their requests.
 */
export async function listMyCollectionCenters(
  token: string,
): Promise<CollectionCenter[]> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/mine`, {
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

/** List a centre's per-centre contributors. **Effective members only.** */
export async function listCenterContributors(
  centerId: string,
  token: string,
): Promise<CenterContributor[]> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/contributors`,
    { headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CenterContributor[];
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

/**
 * Archive a collection center (FR-079). Soft-deletes it (`active = false`,
 * `status = inactive`) so it drops out of the public directory. The backend
 * authorizes the effective owner (center owner or owning-org member) or a
 * maintainer/admin.
 */
export async function archiveCollectionCenter(
  token: string,
  id: string,
): Promise<CollectionCenter> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/${id}/archive`, {
    method: "POST",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Force-archive a collection center (maintainer/admin, FR-080). Soft-deletes
 * it regardless of ownership and writes an audit entry: the recovery path for
 * orphaned or duplicate centers.
 */
export async function forceArchiveCollectionCenter(
  token: string,
  id: string,
): Promise<CollectionCenter> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${id}/force-archive`,
    {
      method: "POST",
      headers: authHeaders(token),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Restore an archived collection center (maintainer/admin). Re-activates it
 * (`active = true`, `status = active`) so it returns to the public directory.
 */
export async function restoreCollectionCenter(
  token: string,
  id: string,
): Promise<CollectionCenter> {
  const res = await fetch(`${apiBaseUrl()}/collection-centers/${id}/restore`, {
    method: "POST",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/**
 * Set a center's operational status (FR-078). `inactive` means "no longer
 * receiving donations": the center stays public but gets a "No recibe
 * donaciones" badge. The backend authorizes effective members (owner,
 * contributors, owning-org members) or a maintainer/admin.
 */
export async function setCollectionCenterStatus(
  token: string,
  id: string,
  status: CollectionCenterStatus,
): Promise<CollectionCenter> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${id}/toggle-status`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as CollectionCenter;
}

/** Add a per-centre contributor by username. **Effective owner only** (FR-084). */
export async function addCenterContributor(
  token: string,
  centerId: string,
  username: string,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/contributors`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ username }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Remove a contributor. The owner may remove anyone; a contributor themselves. */
export async function removeCenterContributor(
  token: string,
  centerId: string,
  userId: string,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/contributors/${userId}`,
    { method: "DELETE", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}
