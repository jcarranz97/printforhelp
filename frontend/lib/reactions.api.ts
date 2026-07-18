/**
 * Raw API calls for polymorphic reactions ("likes"), server-side only.
 * Reads are public (a logged-out visitor still sees counts); reacting /
 * un-reacting requires a token.
 */

import { apiBaseUrl, toApiError } from "@/lib/api";
import type { EntityType } from "@/lib/feed.api";

/** Entity types that accept a reaction. A subset of `EntityType`. */
export type ReactableEntityType =
  | "collection_center"
  | "shipment"
  | "resource"
  | "request"
  | "request_item"
  | "comment";

export type ReactionState = {
  entity_type: EntityType;
  entity_id: string;
  count: number;
  reacted: boolean;
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

/**
 * Reaction `(count, reacted)` for one or many entities of a type. Pass a
 * single id for a detail-page heart, or many for a comment feed (one round
 * trip). `reacted` is always false without a token.
 */
export async function getReactionStates(
  entityType: ReactableEntityType,
  entityIds: string[],
  token?: string,
): Promise<ReactionState[]> {
  if (entityIds.length === 0) {
    return [];
  }
  const params = new URLSearchParams({ entity_type: entityType });
  for (const id of entityIds) {
    params.append("entity_id", id);
  }
  const res = await fetch(`${apiBaseUrl()}/reactions?${params.toString()}`, {
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ReactionState[];
}

/** React ("like") an entity. Idempotent; returns the updated state. */
export async function react(
  token: string,
  entityType: ReactableEntityType,
  entityId: string,
): Promise<ReactionState> {
  const res = await fetch(`${apiBaseUrl()}/reactions`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ entity_type: entityType, entity_id: entityId }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ReactionState;
}

/** Remove the current user's reaction from an entity; returns the state. */
export async function unreact(
  token: string,
  entityType: ReactableEntityType,
  entityId: string,
): Promise<ReactionState> {
  const res = await fetch(
    `${apiBaseUrl()}/reactions/${entityType}/${entityId}`,
    { method: "DELETE", headers: authHeaders(token), cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ReactionState;
}
