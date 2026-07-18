"use server";

/**
 * Server actions for polymorphic reactions ("likes"). They read the auth
 * cookie (server-only) and forward the token to the backend (the real
 * authorization boundary, NFR-006). Client components call them; they never
 * touch the cookie or the backend directly.
 */

import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import * as reactionsApi from "@/lib/reactions.api";
import type { ReactableEntityType, ReactionState } from "@/lib/reactions.api";

async function readToken(): Promise<string | null> {
  const cookieStore = await cookies();
  return cookieStore.get(AUTH_COOKIE_NAME)?.value ?? null;
}

/** Fetch one entity's `(count, reacted)` state (count only for guests). */
export async function fetchReactionStateAction(
  entityType: ReactableEntityType,
  entityId: string,
): Promise<{ count: number; reacted: boolean }> {
  const token = await readToken();
  try {
    const states = await reactionsApi.getReactionStates(
      entityType,
      [entityId],
      token ?? undefined,
    );
    const state = states[0];
    return { count: state?.count ?? 0, reacted: state?.reacted ?? false };
  } catch {
    return { count: 0, reacted: false };
  }
}

export type ReactionSummary = {
  count: number;
  reacted: boolean;
  byAuthor: boolean;
};

/** Batch-fetch reaction states keyed by entity id (for comment feeds). */
export async function fetchReactionStatesAction(
  entityType: ReactableEntityType,
  entityIds: string[],
): Promise<Record<string, ReactionSummary>> {
  const token = await readToken();
  const out: Record<string, ReactionSummary> = {};
  if (entityIds.length === 0) {
    return out;
  }
  try {
    const states = await reactionsApi.getReactionStates(
      entityType,
      entityIds,
      token ?? undefined,
    );
    for (const s of states) {
      out[s.entity_id] = {
        count: s.count,
        reacted: s.reacted,
        byAuthor: s.by_author,
      };
    }
  } catch {
    // Leave `out` partial/empty; the UI falls back to a zero, un-reacted state.
  }
  return out;
}

export type ToggleReactionResult = {
  count: number;
  reacted: boolean;
  /** `"auth"` when the caller is not logged in; `"error"` on a failed call. */
  error: "auth" | "error" | null;
};

/** Toggle the current user's reaction; returns the resulting state. */
export async function toggleReactionAction(
  entityType: ReactableEntityType,
  entityId: string,
  current: { count: number; reacted: boolean },
): Promise<ToggleReactionResult> {
  const token = await readToken();
  if (!token) {
    return { ...current, error: "auth" };
  }
  try {
    const state: ReactionState = current.reacted
      ? await reactionsApi.unreact(token, entityType, entityId)
      : await reactionsApi.react(token, entityType, entityId);
    return { count: state.count, reacted: state.reacted, error: null };
  } catch {
    return { ...current, error: "error" };
  }
}
