/** Raw API calls for Collection Center shipments (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type ShipmentStatus =
  | "receiving"
  | "in_transit"
  | "arrived"
  | "closed"
  | "cancelled";

export type Shipment = {
  id: string;
  collection_center_id: string;
  shipment_date: string;
  status: ShipmentStatus;
  destination: string | null;
  /** Set when the next hop is another Center: this box is a relay leg. */
  destination_collection_center_id: string | null;
  description: string | null;
  /** The QR taped to the box; resolves at /track/{token}. */
  tracking_token: string;
  dispatched_at: string | null;
  arrived_at: string | null;
  arrived_by_id: string | null;
  created_by_id: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type ShipmentPayload = {
  shipment_date: string;
  status?: ShipmentStatus;
  destination?: string | null;
  destination_collection_center_id?: string | null;
  description?: string | null;
};

/** A shipment as it appears in the caller's own cross-centre queue. */
export type MyShipment = Shipment & {
  collection_center_name: string;
  destination_collection_center_name: string | null;
  package_count: number;
};

export type ContentKind = "package" | "box";

/**
 * One manifest line. Everything identifying is null when `redacted` — a box
 * is public but the packages inside it need not be, so a non-public package
 * is counted and never named.
 */
export type ShipmentContentEntry = {
  id: string;
  kind: ContentKind;
  redacted: boolean;
  tracking_group_id: string | null;
  tracking_token: string | null;
  resource_name: string | null;
  quantity: number | null;
  contribution_status: string | null;
  maker_username: string | null;
  maker_full_name: string | null;
  maker_avatar_url: string | null;
  maker_avatar_crop_x: number;
  maker_avatar_crop_y: number;
  maker_avatar_crop_w: number;
  maker_avatar_crop_h: number;
  child_shipment_id: string | null;
  child_status: ShipmentStatus | null;
  child_destination: string | null;
  child_tracking_token: string | null;
  child_package_count: number | null;
  added_at: string;
};

export type ShipmentContents = {
  shipment_id: string;
  contents_total: number;
  child_count: number;
  package_count: number;
  units_total: number;
  hidden_count: number;
  entries: ShipmentContentEntry[];
  can_manage_contents: boolean;
};

/** Exactly one of the three must be set. */
export type ShipmentContentPayload = {
  tracking_token?: string;
  tracking_group_id?: string;
  child_shipment_id?: string;
};

export type ShipmentArrival = {
  shipment: Shipment;
  received: number;
  skipped_already: number;
  skipped_no_center: number;
  packages_total: number;
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/** List a center's shipments (public — always visible, FR-130). */
export async function listShipments(centerId: string): Promise<Shipment[]> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Shipment[];
}

/** Fetch a single shipment by id (public). Returns null when missing. */
export async function getShipment(
  centerId: string,
  shipmentId: string,
): Promise<Shipment | null> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}`,
    { cache: "no-store" },
  );
  if (res.status === 404) {
    return null;
  }
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Shipment;
}

/** Create a shipment (effective member / mod-admin, FR-129). */
export async function createShipment(
  token: string,
  centerId: string,
  payload: ShipmentPayload,
): Promise<Shipment> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Shipment;
}

/** Edit a shipment / change its status (FR-129). */
export async function updateShipment(
  token: string,
  centerId: string,
  shipmentId: string,
  payload: Partial<ShipmentPayload>,
): Promise<Shipment> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}`,
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
  return (await res.json()) as Shipment;
}

/** Soft-delete a shipment (FR-129). */
export async function deleteShipment(
  token: string,
  centerId: string,
  shipmentId: string,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}`,
    { method: "DELETE", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}

/** Read a box's manifest. Public, but redacted for non-custodians (FR-146). */
export async function listShipmentContents(
  centerId: string,
  shipmentId: string,
  token?: string,
): Promise<ShipmentContents> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}/contents`,
    { headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ShipmentContents;
}

/** Pack a package or nest another box (FR-138). */
export async function addShipmentContent(
  token: string,
  centerId: string,
  shipmentId: string,
  payload: ShipmentContentPayload,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}/contents`,
    {
      method: "POST",
      headers: { ...authHeaders(token), "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      cache: "no-store",
    },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
}

/** Unpack one manifest line (soft delete, FR-147). */
export async function removeShipmentContent(
  token: string,
  centerId: string,
  shipmentId: string,
  contentId: string,
): Promise<void> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}/contents/${contentId}`,
    { method: "DELETE", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}

/** Move a box through its lifecycle: dispatch, arrive, or re-receive. */
export async function shipmentLifecycle(
  token: string,
  centerId: string,
  shipmentId: string,
  action: "dispatch" | "arrive" | "receive-contents",
): Promise<ShipmentArrival | Shipment> {
  const res = await fetch(
    `${apiBaseUrl()}/collection-centers/${centerId}/shipments/${shipmentId}/${action}`,
    { method: "POST", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ShipmentArrival | Shipment;
}

/** Every shipment at a centre the caller staffs, newest first (FR-129). */
export async function listMyShipments(token: string): Promise<MyShipment[]> {
  const res = await fetch(`${apiBaseUrl()}/shipments/mine`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as MyShipment[];
}
