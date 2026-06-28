/** Raw API calls for Requests + RequestItems (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type RequestStatus = "open" | "fulfilled" | "closed";

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
  part_id: string;
  quantity: number | null;
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

export type RequestDetail = RequestSummary & { items: RequestItem[] };

export type CreateRequestItem = {
  part_id: string;
  quantity?: number | null;
  description?: string;
  deadline?: string;
};

export type CreateRequestPayload = {
  title: string;
  description?: string;
  deadline?: string;
  items: CreateRequestItem[];
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** List campaigns, `open` by default (public, FR-040). */
export async function listRequests(
  status?: RequestStatus,
): Promise<RequestSummary[]> {
  const query = status ? `?status=${status}` : "";
  const res = await fetch(`${apiBaseUrl()}/requests${query}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as RequestSummary[];
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
