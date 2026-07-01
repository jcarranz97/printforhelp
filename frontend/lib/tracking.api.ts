/** Raw API calls for item tracking (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type TrackingVisibility = "private" | "group" | "public";
export type TrackingTargetKind = "group" | "item";

export type TrackingRecordAuthor = {
  id: string | null;
  username: string | null;
};

export type TrackingRecord = {
  id: string;
  target_kind: TrackingTargetKind;
  target_token: string;
  /** For item records, the 1-based unit number within the group. */
  item_sequence: number | null;
  author: TrackingRecordAuthor;
  description: string;
  tags: string[];
  created_at: string;
  can_edit_tags: boolean;
};

export type PublicTracking = {
  target_kind: TrackingTargetKind;
  tracking_token: string;
  visibility: TrackingVisibility;
  resource_name: string;
  resource_image_url: string | null;
  contribution_status: string;
  quantity: number;
  item_sequence: number | null;
  records: TrackingRecord[];
  can_contribute: boolean;
};

export type TrackingItem = {
  id: string;
  tracking_token: string;
  sequence: number;
};

export type TrackingGroupMember = {
  id: string;
  username: string;
};

export type OwnerTracking = {
  group_id: string;
  contribution_id: string;
  tracking_token: string;
  visibility: TrackingVisibility;
  quantity: number;
  resource_name: string;
  resource_image_url: string | null;
  members: TrackingGroupMember[];
  items: TrackingItem[];
  records: TrackingRecord[];
};

export type AddRecordPayload = {
  description: string;
  tags: string[];
  display_anonymous: boolean;
};

function authHeaders(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}

/**
 * Browser-facing base URL for the backend (`NEXT_PUBLIC_API_URL`), used to
 * build `<img>` sources for public QR codes that the browser fetches
 * directly (the QR endpoint is unauthenticated).
 */
export function publicApiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8100/api/v1";
}

/** Browser URL of the PNG QR code for one tracking token. */
export function trackQrImageUrl(token: string): string {
  return `${publicApiBaseUrl()}/track/${token}/qr.png`;
}

/** Public tracking page data. `token` (auth) reveals private/group timelines.
 *
 * On a group token, `includeItemUpdates` (default true) folds per-item
 * updates into the timeline; pass false for group-level updates only.
 */
export async function getPublicTracking(
  trackingToken: string,
  authToken?: string,
  includeItemUpdates = true,
): Promise<PublicTracking> {
  const query = includeItemUpdates ? "" : "?include_item_updates=false";
  const res = await fetch(`${apiBaseUrl()}/track/${trackingToken}${query}`, {
    headers: authToken ? authHeaders(authToken) : {},
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as PublicTracking;
}

/** Append a record after scanning a QR (auth optional — guests are anonymous). */
export async function addTrackingRecord(
  trackingToken: string,
  payload: AddRecordPayload,
  authToken?: string,
): Promise<TrackingRecord> {
  const res = await fetch(`${apiBaseUrl()}/track/${trackingToken}/records`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? authHeaders(authToken) : {}),
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as TrackingRecord;
}

/** Generate the tracking group + one QR item per unit (maker/admin). */
export async function generateTracking(
  contributionId: string,
  token: string,
): Promise<OwnerTracking> {
  const res = await fetch(
    `${apiBaseUrl()}/tracking/contributions/${contributionId}`,
    { method: "POST", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as OwnerTracking;
}

/** Owner view of a Contribution's tracking (throws 404 if not generated). */
export async function getOwnerTracking(
  contributionId: string,
  token: string,
): Promise<OwnerTracking> {
  const res = await fetch(
    `${apiBaseUrl()}/tracking/contributions/${contributionId}`,
    { headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as OwnerTracking;
}

/** Set visibility and the named group-visibility members (maker/admin). */
export async function updateTracking(
  groupId: string,
  payload: { visibility: TrackingVisibility; member_usernames: string[] },
  token: string,
): Promise<OwnerTracking> {
  const res = await fetch(`${apiBaseUrl()}/tracking/groups/${groupId}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as OwnerTracking;
}

/** Replace a record's tags (author / contribution owner / maintainer). */
export async function editRecordTags(
  recordId: string,
  tags: string[],
  token: string,
): Promise<TrackingRecord> {
  const res = await fetch(`${apiBaseUrl()}/tracking/records/${recordId}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ tags }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as TrackingRecord;
}

/** Fetch a QR bundle (pdf/png) with the caller's bearer token, for proxying. */
export async function fetchQrBundle(
  groupId: string,
  format: "pdf" | "png",
  token: string,
): Promise<Response> {
  return fetch(
    `${apiBaseUrl()}/tracking/groups/${groupId}/qr-bundle.${format}`,
    { headers: authHeaders(token), cache: "no-store" },
  );
}
