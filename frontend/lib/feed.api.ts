/**
 * Raw API calls for the polymorphic comments + activity feed
 * (server-side only). Reads are public; writes require a token.
 */

import { apiBaseUrl, toApiError } from "@/lib/api";

export type EntityType =
  | "collection_center"
  | "shipment"
  | "resource"
  | "request";

export type ActorSummary = { id: string; username: string };

export type Comment = {
  id: string;
  entity_type: EntityType;
  entity_id: string;
  author: ActorSummary;
  body: string;
  edited_at: string | null;
  created_at: string;
  updated_at: string;
  /** Usernames in the body that resolve to a real active user. */
  mentions: string[];
};

export type ActivityAction =
  | "created"
  | "updated"
  | "status_changed"
  | "deleted"
  | "commented"
  | "comment_edited"
  | "comment_deleted";

export type ActivityEntry = {
  id: string;
  entity_type: EntityType;
  entity_id: string;
  actor: ActorSummary;
  action: ActivityAction;
  changes: Record<string, unknown>;
  created_at: string;
};

function authHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function entityQuery(entityType: EntityType, entityId: string): string {
  return new URLSearchParams({
    entity_type: entityType,
    entity_id: entityId,
  }).toString();
}

/** List comments for an entity (public, newest first, FR-131). */
export async function listComments(
  entityType: EntityType,
  entityId: string,
): Promise<Comment[]> {
  const res = await fetch(
    `${apiBaseUrl()}/comments?${entityQuery(entityType, entityId)}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Comment[];
}

/** List the activity timeline for an entity (public, FR-133). */
export async function listActivity(
  entityType: EntityType,
  entityId: string,
): Promise<ActivityEntry[]> {
  const res = await fetch(
    `${apiBaseUrl()}/activity?${entityQuery(entityType, entityId)}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as ActivityEntry[];
}

/** Post a Markdown comment (authenticated, FR-131). */
export async function createComment(
  token: string,
  entityType: EntityType,
  entityId: string,
  body: string,
): Promise<Comment> {
  const res = await fetch(`${apiBaseUrl()}/comments`, {
    method: "POST",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({
      entity_type: entityType,
      entity_id: entityId,
      body,
    }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Comment;
}

/** Edit a comment body (author only, FR-132). */
export async function updateComment(
  token: string,
  commentId: string,
  body: string,
): Promise<Comment> {
  const res = await fetch(`${apiBaseUrl()}/comments/${commentId}`, {
    method: "PATCH",
    headers: { ...authHeaders(token), "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
    cache: "no-store",
  });
  if (!res.ok) {
    throw await toApiError(res);
  }
  return (await res.json()) as Comment;
}

/** Soft-delete a comment (author or mod/admin, FR-132). */
export async function deleteComment(
  token: string,
  commentId: string,
): Promise<void> {
  const res = await fetch(`${apiBaseUrl()}/comments/${commentId}`, {
    method: "DELETE",
    headers: authHeaders(token),
    cache: "no-store",
  });
  if (!res.ok && res.status !== 204) {
    throw await toApiError(res);
  }
}
