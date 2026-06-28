/** Raw API calls for Collection Center shipments (server-side only). */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type ShipmentStatus = "receiving" | "closed" | "cancelled";

export type Shipment = {
  id: string;
  collection_center_id: string;
  shipment_date: string;
  status: ShipmentStatus;
  destination: string | null;
  description: string | null;
  created_by_id: string;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type ShipmentPayload = {
  shipment_date: string;
  status?: ShipmentStatus;
  destination?: string | null;
  description?: string | null;
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
