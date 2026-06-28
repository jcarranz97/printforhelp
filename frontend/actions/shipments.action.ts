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
