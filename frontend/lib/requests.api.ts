/** Raw API calls for Requests + RequestItems (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type RequestStatus = "open" | "fulfilled" | "closed";

/** Derived fulfillment bucket shared by items and campaigns. */
export type HelpState = "needs_help" | "committed" | "completed";

export type RequestItemProgress = {
  target_quantity: number | null;
  claimed_quantity: number;
  at_center_quantity: number;
  committed_quantity: number;
  remaining: number | null;
};

export type RequestItem = {
  id: string;
  request_id: string;
  /** Stable, per-request sequential number (1, 2, ...); drives label + URL. */
  item_number: number;
  resource_id: string;
  quantity: number | null;
  /** Chosen unit of measure for the quantity (e.g. "litros"); null = pieces. */
  unit: string | null;
  /** Per-item subset of the request's preferred centers (empty = all apply). */
  preferred_collection_center_ids: string[];
  description: string | null;
  deadline: string | null;
  status: RequestStatus;
  closed_reason: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
  progress: RequestItemProgress;
};

export type RequestSummary = {
  id: string;
  title: string;
  description: string | null;
  image_url: string | null;
  deadline: string | null;
  requester_user_id: string | null;
  requester_organization_id: string | null;
  created_by_id: string;
  preferred_collection_center_ids: string[];
  status: RequestStatus;
  closed_reason: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

/** A campaign in the directory, with its derived help state + last activity. */
export type RequestListEntry = RequestSummary & {
  help_state: HelpState;
  last_activity_at: string;
};

export type RequestDetail = RequestSummary & { items: RequestItem[] };

/** A single item with Resource context + last-activity, for its detail page. */
export type RequestItemDetail = RequestItem & {
  resource_name: string;
  resource_description: string | null;
  resource_image_url: string | null;
  resource_source_url: string | null;
  request_title: string;
  request_status: RequestStatus;
  last_activity_at: string;
};

export type ContributionStatus =
  | "claimed"
  | "prepared"
  | "delivered"
  | "received"
  | "released";

/** A public commitment shown on an item's detail page. */
export type ItemCommitment = {
  id: string;
  maker_username: string;
  quantity: number;
  status: ContributionStatus;
  collection_center_name: string | null;
  claimed_at: string;
  prepared_at: string | null;
  delivered_at: string | null;
  received_at: string | null;
};

export type CreateRequestItem = {
  resource_id: string;
  quantity?: number | null;
  unit?: string | null;
  description?: string;
  deadline?: string;
};

/** Fields editable on an existing item (effective requester). */
export type UpdateRequestItemPayload = {
  quantity?: number | null;
  unit?: string | null;
  description?: string | null;
  preferred_collection_center_ids?: string[];
};

export type CreateRequestPayload = {
  title: string;
  description?: string;
  image_url?: string;
  deadline?: string;
  preferred_collection_center_ids?: string[];
  items: CreateRequestItem[];
};

export type UpdateRequestPayload = {
  title?: string;
  description?: string | null;
  image_url?: string | null;
  deadline?: string | null;
  preferred_collection_center_ids?: string[];
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * List campaigns with a derived help state (public, FR-040). With no
 * `status` filter, returns open and fulfilled campaigns.
 */
export async function listRequests(
  status?: RequestStatus,
): Promise<RequestListEntry[]> {
  const query = status ? `?status=${status}` : "";
  const res = await fetch(`${apiBaseUrl()}/requests${query}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestListEntry[];
}

/**
 * Fetch one item by its per-request number, with Resource context + last
 * activity (public), or null when the item/number does not exist.
 */
export async function getRequestItem(
  requestId: string,
  itemNumber: string,
): Promise<RequestItemDetail | null> {
  const res = await fetch(
    `${apiBaseUrl()}/requests/${requestId}/items/${itemNumber}`,
    { cache: "no-store" },
  );
  // 404 = no such item; 422 = the number segment was not an integer.
  if (res.status === 404 || res.status === 422) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestItemDetail;
}

/** List the public commitments on one item, by its number (public). */
export async function listItemCommitments(
  requestId: string,
  itemNumber: string,
): Promise<ItemCommitment[]> {
  const res = await fetch(
    `${apiBaseUrl()}/requests/${requestId}/items/${itemNumber}/contributions`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ItemCommitment[];
}

/** Fetch a Request with its items + per-item progress, or null. */
export async function getRequest(id: string): Promise<RequestDetail | null> {
  const res = await fetch(`${apiBaseUrl()}/requests/${id}`, {
    cache: "no-store",
  });
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestDetail;
}

/** Create a Request with at least one item (FR-038). */
export async function createRequest(
  payload: CreateRequestPayload,
  token: string,
): Promise<RequestDetail> {
  const res = await fetch(`${apiBaseUrl()}/requests`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestDetail;
}

/** Edit campaign metadata while the Request is open (FR-042). */
export async function updateRequest(
  id: string,
  payload: UpdateRequestPayload,
  token: string,
): Promise<RequestDetail> {
  const res = await fetch(`${apiBaseUrl()}/requests/${id}`, {
    method: "PUT",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestDetail;
}

/** Close a Request, cascading items + claimed Contributions (FR-049). */
export async function closeRequest(
  id: string,
  reason: string | null,
  token: string,
): Promise<RequestDetail> {
  const res = await fetch(`${apiBaseUrl()}/requests/${id}/close`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestDetail;
}

/** Add a new RequestItem to an open campaign (FR-122). */
export async function addRequestItem(
  requestId: string,
  payload: CreateRequestItem,
  token: string,
): Promise<RequestItem> {
  const res = await fetch(`${apiBaseUrl()}/requests/${requestId}/items`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestItem;
}

/** Edit an open item's target quantity/unit (FR-120). */
export async function updateRequestItem(
  requestId: string,
  itemId: string,
  payload: UpdateRequestItemPayload,
  token: string,
): Promise<RequestItem> {
  const res = await fetch(
    `${apiBaseUrl()}/requests/${requestId}/items/${itemId}`,
    {
      method: "PATCH",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestItem;
}

/** Remove an item from an open campaign (FR-123). */
export async function removeRequestItem(
  requestId: string,
  itemId: string,
  token: string,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/requests/${requestId}/items/${itemId}`,
    { method: "DELETE", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Close one item without closing the parent campaign (FR-124). */
export async function closeRequestItem(
  requestId: string,
  itemId: string,
  token: string,
): Promise<RequestItem> {
  const res = await fetch(
    `${apiBaseUrl()}/requests/${requestId}/items/${itemId}/close`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify({ reason: null }),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestItem;
}
