"use server";

/**
 * Server actions for admin user management. Each action re-reads the
 * auth cookie and re-verifies the caller is an admin server-side
 * (NFR-006) before forwarding the request to the backend.
 */

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import { fetchMe, type UserRole } from "@/lib/auth.api";
import * as usersApi from "@/lib/users.api";

const ADMIN_USERS_PATH = "/admin/users";

export type ActionState = { error: string | null; success: boolean };

/** Resolve the caller's token, redirecting unless they are an admin. */
async function requireAdminToken(): Promise<string> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    redirect("/login?next=/admin/users");
  }
  const me = await fetchMe(token);
  if (!me || me.role !== "admin") {
    redirect("/");
  }
  return token;
}

/** Translate a backend error into a Spanish, user-facing message. */
function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    switch (error.code) {
      case "USERNAME_TAKEN":
        return "Ese nombre de usuario ya está en uso.";
      case "WEAK_PASSWORD":
        return "La contraseña debe tener al menos 8 caracteres, con una letra y un número.";
      case "LOCKOUT_PROTECTION":
        return "No puedes degradar ni desactivar al último administrador activo.";
      case "USER_NOT_FOUND":
        return "El usuario ya no existe.";
      default:
        return "No se pudo completar la acción. Inténtalo de nuevo.";
    }
  }
  return "No se pudo completar la acción. Inténtalo de nuevo.";
}

/** Create a new account (used with `useActionState`). */
export async function createUserAction(
  _prevState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const token = await requireAdminToken();

  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");
  const role = String(formData.get("role") ?? "user") as UserRole;

  if (!username || !password) {
    return { error: "Completa el usuario y la contraseña.", success: false };
  }

  try {
    await usersApi.createUser(token, { username, password, role });
  } catch (error) {
    return { error: messageFor(error), success: false };
  }

  revalidatePath(ADMIN_USERS_PATH);
  return { error: null, success: true };
}

/** Change a user's role (called directly from the table). */
export async function updateRoleAction(
  userId: string,
  role: UserRole,
): Promise<{ error: string | null }> {
  const token = await requireAdminToken();
  try {
    await usersApi.updateUserRole(token, userId, role);
  } catch (error) {
    return { error: messageFor(error) };
  }
  revalidatePath(ADMIN_USERS_PATH);
  return { error: null };
}

/** Activate or deactivate a user (called directly from the table). */
export async function setActiveAction(
  userId: string,
  active: boolean,
): Promise<{ error: string | null }> {
  const token = await requireAdminToken();
  try {
    await usersApi.setUserActive(token, userId, active);
  } catch (error) {
    return { error: messageFor(error) };
  }
  revalidatePath(ADMIN_USERS_PATH);
  return { error: null };
}

/** Set a new password for a user (used with `useActionState`). */
export async function resetPasswordAction(
  _prevState: ActionState,
  formData: FormData,
): Promise<ActionState> {
  const token = await requireAdminToken();

  const userId = String(formData.get("userId") ?? "");
  const newPassword = String(formData.get("new_password") ?? "");

  if (!userId || !newPassword) {
    return { error: "Ingresa la nueva contraseña.", success: false };
  }

  try {
    await usersApi.resetUserPassword(token, userId, newPassword);
  } catch (error) {
    return { error: messageFor(error), success: false };
  }

  revalidatePath(ADMIN_USERS_PATH);
  return { error: null, success: true };
}
