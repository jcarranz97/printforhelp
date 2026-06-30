/** Raw API calls for the Contribution lifecycle (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type ContributionStatus =
  | "claimed"
  | "prepared"
  | "delivered"
  | "received"
  | "released";

export type Contribution = {
  id: string;
  request_item_id: string;
  maker_id: string;
  collection_center_id: string | null;
  quantity: number;
  notes: string | null;
  status: ContributionStatus;
  claimed_at: string;
  prepared_at: string | null;
  delivered_at: string | null;
  received_at: string | null;
  received_by_id: string | null;
  auto_received: boolean;
  released_at: string | null;
  released_reason: string | null;
  tags: string[];
  active: boolean;
  created_at: string;
  updated_at: string;
};

/** A Contribution enriched with its Resource + Request context (the `/me` list). */
export type MyContribution = Contribution & {
  request_id: string;
  request_title: string;
  resource_id: string;
  resource_name: string;
  resource_image_url: string | null;
  collection_center_name: string | null;
};

export type CreateContributionPayload = {
  request_item_id: string;
  /** Optional at claim time — a drop-off center can be set later. */
  collection_center_id?: string;
  quantity: number;
  notes?: string;
};

export type UpdateContributionPayload = {
  quantity?: number;
  notes?: string;
  collection_center_id?: string | null;
  tags?: string[];
};

/** The lifecycle transitions a maker (or center member) can trigger. */
export type ContributionAction =
  | "mark-prepared"
  | "mark-delivered"
  | "confirm-received"
  | "release";

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/** Claim a quantity of an open RequestItem at a center (FR-050). */
export async function createContribution(
  payload: CreateContributionPayload,
  token: string,
): Promise<Contribution> {
  const res = await fetch(`${apiBaseUrl()}/contributions`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Contribution;
}

/** Edit a Contribution — quantity/notes (claimed) or center (claimed/prepared). */
export async function updateContribution(
  id: string,
  payload: UpdateContributionPayload,
  token: string,
): Promise<Contribution> {
  const res = await fetch(`${apiBaseUrl()}/contributions/${id}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Contribution;
}

/** List the caller's own Contributions, filterable by status. */
export async function listMyContributions(
  token: string,
  status?: ContributionStatus,
): Promise<MyContribution[]> {
  const query = status ? `?status=${status}` : "";
  const res = await fetch(`${apiBaseUrl()}/contributions/me${query}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as MyContribution[];
}

/** Advance a Contribution through one lifecycle transition. */
export async function advanceContribution(
  id: string,
  action: ContributionAction,
  token: string,
): Promise<Contribution> {
  const res = await fetch(`${apiBaseUrl()}/contributions/${id}/${action}`, {
    method: "POST",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Contribution;
}
