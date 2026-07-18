"use server";

/**
 * Server actions for comments on the community feed. Reads are public and
 * happen server-side in the page; these mutating actions forward the auth
 * token to the backend (the real authorization boundary, NFR-006) and
 * revalidate the page so the server-rendered feed refreshes. `path` is
 * the route to revalidate (the center page or a shipment detail page);
 * it only busts the render cache, so accepting it from the client is
 * safe — the real authorization happens against the forwarded token.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import type { Dictionary } from "@/i18n/dictionaries";
import { getServerI18n } from "@/i18n/server";
import type { EntityType } from "@/lib/feed.api";
import * as feedApi from "@/lib/feed.api";

export type FeedActionResult = { error: string | null };

function messageFor(error: unknown, t: Dictionary["feed"]): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "COMMENT_NOT_AUTHOR":
        return t.errorNotAuthor;
      case "COMMENT_DELETE_FORBIDDEN":
        return t.errorDeleteForbidden;
      case "INVALID_ENTITY_REFERENCE":
      case "COMMENT_NOT_FOUND":
      case "INVALID_REPLY_PARENT":
        return t.errorNotFound;
      case "VALIDATION_ERROR":
        return t.errorEmpty;
      default:
        return t.errorGeneric;
    }
  }
  return t.errorGeneric;
}

async function tokenOrError(
  t: Dictionary["feed"],
): Promise<{ token: string } | { error: string }> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { error: t.errorAuth };
  }
  return { token };
}

/**
 * Post a Markdown comment on an entity (FR-131). Passing `parentCommentId`
 * posts it as a reply (Instagram-style single-level thread).
 */
export async function postCommentAction(
  path: string,
  entityType: EntityType,
  entityId: string,
  body: string,
  parentCommentId?: string | null,
): Promise<FeedActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.feed;
  if (!body.trim()) {
    return { error: t.errorEmpty };
  }
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await feedApi.createComment(
      auth.token,
      entityType,
      entityId,
      body.trim(),
      parentCommentId,
    );
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(path);
  return { error: null };
}

/** Edit a comment body (author only, FR-132). */
export async function editCommentAction(
  path: string,
  commentId: string,
  body: string,
): Promise<FeedActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.feed;
  if (!body.trim()) {
    return { error: t.errorEmpty };
  }
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await feedApi.updateComment(auth.token, commentId, body.trim());
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(path);
  return { error: null };
}

/** Soft-delete a comment (author or mod/admin, FR-132). */
export async function deleteCommentAction(
  path: string,
  commentId: string,
): Promise<FeedActionResult> {
  const { dict } = await getServerI18n();
  const t = dict.feed;
  const auth = await tokenOrError(t);
  if ("error" in auth) {
    return { error: auth.error };
  }
  try {
    await feedApi.deleteComment(auth.token, commentId);
  } catch (error) {
    return { error: messageFor(error, t) };
  }
  revalidatePath(path);
  return { error: null };
}
