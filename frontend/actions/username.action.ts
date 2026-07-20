"use server";

/** Server action for renaming the caller's public handle from settings. */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { changeUsername } from "@/lib/users.api";

export type ChangeUsernameResult =
  | { ok: true; username: string }
  | { ok: false; errorCode: string };

/**
 * Rename the caller. Errors come back as stable codes rather than messages so
 * the client can localise them (and tell "taken" apart from "too soon", which
 * need very different wording).
 */
export async function changeUsernameAction(
  username: string,
): Promise<ChangeUsernameResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { ok: false, errorCode: "AUTH" };
  }
  try {
    const user = await changeUsername(token, username.trim());
    // The handle appears in the header greeting and every profile link.
    revalidatePath("/", "layout");
    return { ok: true, username: user.username };
  } catch (error) {
    if (error instanceof ApiError) {
      // A malformed handle is a plain 422 with no domain code.
      return { ok: false, errorCode: error.code || "INVALID_USERNAME" };
    }
    return { ok: false, errorCode: "UPDATE" };
  }
}
