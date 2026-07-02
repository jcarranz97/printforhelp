"use server";

/** Server actions for the caller's own user flags (e.g. the maker trait). */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME } from "@/lib/api";
import { setOwnFlag } from "@/lib/users.api";

/** Answer the "are you a maker?" prompt (Yes/No). Returns whether it saved. */
export async function setMakerFlagAction(
  value: boolean,
): Promise<{ ok: boolean }> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { ok: false };
  }
  try {
    await setOwnFlag(token, "maker", value);
  } catch {
    return { ok: false };
  }
  // Refresh server components (the header greeting reads the flag).
  revalidatePath("/", "layout");
  return { ok: true };
}
