"use server";

/**
 * Server actions for Collection Center shipments. Each mutating action
 * re-reads the auth cookie and forwards the token to the backend, which
 * is the real authorization boundary (effective member or mod/admin,
 * NFR-006 / FR-129). On success the center detail path is revalidated so
 * the server-rendered shipments list refreshes.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import { listCollectionCenters } from "@/lib/collection-centers.api";
import * as shipmentsApi from "@/lib/shipments.api";
import type { ShipmentPayload } from "@/lib/shipments.api";

export type ShipmentActionResult = { error: string | null };

function messageFor(error: unknown, t: Dictionary["shipments"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "NOT_EFFECTIVE_MEMBER":
        return t.errorNotMember;
      case "COLLECTION_CENTER_NOT_FOUND":
      case "SHIPMENT_NOT_FOUND":
        return t.errorNotFound;
      case "VALIDATION_ERROR":
        return t.errorValidation;
      case "ALREADY_PACKED":
        return t.errorAlreadyPacked;
      case "SHIPMENT_CYCLE":
        return t.errorCycle;
      case "SHIPMENT_TOO_DEEP":
        return t.errorTooDeep;
      case "SHIPMENT_LOCKED":
        return t.errorLocked;
      case "INVALID_SHIPMENT_TRANSITION":
        return t.errorTransition;
      case "TRACKING_NOT_FOUND":
        return t.errorTokenNotFound;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

async function tokenOrError(
  t: Dictionary["shipments"],
): Promise<{ token: string } | { error: string }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { error: t.errorAuth };
  }
  return { token };
}

/** Create a shipment on a center (FR-129). */
export async function createShipmentAction(
  centerId: string,
  payload: ShipmentPayload,
): Promise<ShipmentActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await shipmentsApi.createShipment(auth.token, centerId, payload);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  return { error: null };
}

/** Edit a shipment or change its status (FR-129). */
export async function updateShipmentAction(
  centerId: string,
  shipmentId: string,
  payload: Partial<ShipmentPayload>,
): Promise<ShipmentActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await shipmentsApi.updateShipment(
      auth.token,
      centerId,
      shipmentId,
      payload,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  revalidatePath(`/centers/${centerId}/shipments/${shipmentId}`);
  return { error: null };
}

/** Soft-delete a shipment (FR-129). */
export async function deleteShipmentAction(
  centerId: string,
  shipmentId: string,
): Promise<ShipmentActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await shipmentsApi.deleteShipment(auth.token, centerId, shipmentId);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  return { error: null };
}

/** Pack a package (or nest another box) into this box (FR-138). */
export async function addShipmentContentAction(
  centerId: string,
  shipmentId: string,
  payload: shipmentsApi.ShipmentContentPayload,
): Promise<ShipmentActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await shipmentsApi.addShipmentContent(
      auth.token,
      centerId,
      shipmentId,
      payload,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}/shipments/${shipmentId}`);
  return { error: null };
}

/** Unpack one manifest line (FR-147). */
export async function removeShipmentContentAction(
  centerId: string,
  shipmentId: string,
  contentId: string,
): Promise<ShipmentActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await shipmentsApi.removeShipmentContent(
      auth.token,
      centerId,
      shipmentId,
      contentId,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}/shipments/${shipmentId}`);
  return { error: null };
}

export type ShipmentLifecycleResult = ShipmentActionResult & {
  /** Populated by `arrive` / `receive-contents` so the UI can report counts. */
  arrival?: shipmentsApi.ShipmentArrival;
};

/** Dispatch, sign for, or re-run the bulk receipt on a box (FR-141/143). */
export async function shipmentLifecycleAction(
  centerId: string,
  shipmentId: string,
  action: "dispatch" | "arrive" | "receive-contents",
): Promise<ShipmentLifecycleResult> {
  const { dict } = await getServerI18n();
  const t = dict.shipments;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  let result: shipmentsApi.ShipmentArrival | shipmentsApi.Shipment;
  try {
    result = await shipmentsApi.shipmentLifecycle(
      auth.token,
      centerId,
      shipmentId,
      action,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(`/centers/${centerId}`);
  revalidatePath(`/centers/${centerId}/shipments/${shipmentId}`);
  return {
    error: null,
    arrival: "packages_total" in result ? result : undefined,
  };
}

export type DestinationOption = { id: string; name: string; city: string };

/**
 * Verified, listed centres a box can be routed to (FR-142).
 *
 * Fetched lazily by the form rather than threaded down from the page: the
 * directory can be long, and only the handful of members who actually open the
 * shipment form need it.
 */
export async function listDestinationCentersAction(
  excludeCenterId: string,
): Promise<DestinationOption[]> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  try {
    const centers = await listCollectionCenters({}, token);
    return centers
      .filter((c) => c.id !== excludeCenterId)
      .map((c) => ({ id: c.id, name: c.name, city: c.city }));
  } catch {
    // A picker that cannot load must not block creating an ordinary shipment.
    return [];
  }
}
