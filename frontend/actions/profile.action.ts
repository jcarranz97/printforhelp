"use server";

/**
 * Server actions for the caller's own public profile (name, bio, avatar).
 *
 * The JWT lives in an httpOnly cookie the browser cannot read, so both the
 * avatar upload and the profile save run server-side. On a successful save we
 * revalidate the root layout so the header avatar/greeting re-render with the
 * new picture.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import type { CurrentUser } from "@/lib/auth.api";
import { updateMyAvatar, updateMyProfile } from "@/lib/users.api";
import type {
  AvatarUpdatePayload,
  ProfileUpdatePayload,
} from "@/lib/users.api";
import { uploadImage } from "@/lib/uploads.api";

export type UpdateProfileResult =
  | { ok: true; user: CurrentUser }
  | { ok: false; errorCode: string };

/** Save the caller's name and bio. */
export async function updateProfileAction(
  payload: ProfileUpdatePayload,
): Promise<UpdateProfileResult> {
  return save(() => updateMyProfile, payload);
}

/**
 * Save the caller's profile picture and crop (or remove it with a null URL).
 * Applied as soon as the picture is cropped, independently of the name/bio
 * form, so neither save clobbers the other's unsaved state.
 */
export async function updateAvatarAction(
  payload: AvatarUpdatePayload,
): Promise<UpdateProfileResult> {
  return save(() => updateMyAvatar, payload);
}

async function save<P extends ProfileUpdatePayload | AvatarUpdatePayload>(
  pick: () => (token: string, payload: P) => Promise<CurrentUser>,
  payload: P,
): Promise<UpdateProfileResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { ok: false, errorCode: "AUTH" };
  }
  try {
    const user = await pick()(token, payload);
    // The header avatar + maker greeting are server-rendered from /auth/me.
    revalidatePath("/", "layout");
    return { ok: true, user };
  } catch (error) {
    return {
      ok: false,
      errorCode: error instanceof ApiError ? error.code : "UPDATE",
    };
  }
}

export type UploadAvatarResult = { url: string } | { errorCode: string };

/** Upload a new avatar image and return its stored public URL. */
export async function uploadAvatarAction(
  formData: FormData,
): Promise<UploadAvatarResult> {
  const token = (await cookies()).get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { errorCode: "AUTH" };
  }
  const file = formData.get("file");
  if (!(file instanceof File) || file.size === 0) {
    return { errorCode: "NO_FILE" };
  }
  try {
    const url = await uploadImage(file, token);
    return { url };
  } catch (error) {
    return { errorCode: error instanceof ApiError ? error.code : "UPLOAD" };
  }
}
