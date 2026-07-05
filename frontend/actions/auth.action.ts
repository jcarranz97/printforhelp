"use server";

/**
 * Server actions for authentication. This is the only place that reads
 * and writes the auth cookie (cookie access is server-only).
 */

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { AUTH_COOKIE_NAME, ApiError } from "@/lib/api";
import {
  type CurrentUser,
  chooseUsernameRequest,
  fetchMe,
  forgotPasswordRequest,
  googleLoginRequest,
  loginRequest,
  registerRequest,
  resetPasswordRequest,
} from "@/lib/auth.api";
import { getServerI18n } from "@/i18n/server";

const SEVEN_DAYS_SECONDS = 60 * 60 * 24 * 7;

export type LoginState = { error: string | null };

/** Per-field validation errors for the registration form. */
export type RegisterFieldErrors = {
  full_name?: string;
  username?: string;
  email?: string;
  password?: string;
};

export type RegisterState = {
  /** Form-level error not tied to a single field (e.g. network failure). */
  error: string | null;
  /** Field-level errors keyed by input name, rendered via `FieldError`. */
  fieldErrors: RegisterFieldErrors;
  /** Submitted values echoed back so the form is not cleared on error. */
  values: { full_name: string; username: string; email: string };
};

/** Persist the JWT in the httpOnly session cookie. */
async function setSessionCookie(token: string): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.set(AUTH_COOKIE_NAME, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: SEVEN_DAYS_SECONDS,
  });
}

/** Resolve the current user from the auth cookie, or null. */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return null;
  }
  try {
    return await fetchMe(token);
  } catch {
    return null;
  }
}

/** Handle the login form submission (used with `useActionState`). */
export async function loginAction(
  _prevState: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const { dict } = await getServerI18n();
  const t = dict.login;

  const username = String(formData.get("username") ?? "").trim();
  const password = String(formData.get("password") ?? "");

  if (!username || !password) {
    return { error: t.errorMissing };
  }

  let token: string;
  try {
    const data = await loginRequest(username, password);
    token = data.access_token;
  } catch (error) {
    if (error instanceof ApiError && error.code === "INACTIVE_USER") {
      return { error: t.errorInactive };
    }
    if (error instanceof ApiError && error.status === 401) {
      return { error: t.errorInvalid };
    }
    return { error: t.errorGeneric };
  }

  await setSessionCookie(token);

  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect("/");
}

export type GoogleLoginResult = { error: string | null };

/** Exchange a Google id_token for our session cookie. */
export async function googleLoginAction(
  idToken: string,
): Promise<GoogleLoginResult> {
  const { dict } = await getServerI18n();

  if (!idToken) {
    return { error: dict.login.googleError };
  }

  try {
    const data = await googleLoginRequest(idToken);
    await setSessionCookie(data.access_token);
  } catch (error) {
    if (error instanceof ApiError && error.code === "INACTIVE_USER") {
      return { error: dict.login.errorInactive };
    }
    return { error: dict.login.googleError };
  }

  return { error: null };
}

/** Handle the registration form submission (used with `useActionState`). */
export async function registerAction(
  _prevState: RegisterState,
  formData: FormData,
): Promise<RegisterState> {
  const { dict } = await getServerI18n();
  const t = dict.register;

  const fullName = String(formData.get("full_name") ?? "").trim();
  const username = String(formData.get("username") ?? "").trim();
  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();
  const password = String(formData.get("password") ?? "");

  // Echo the typed values back so the form keeps its content on error
  // (password is intentionally not echoed — the user re-enters it).
  const values = { full_name: fullName, username, email };
  const fail = (
    fieldErrors: RegisterFieldErrors,
    error: string | null = null,
  ): RegisterState => ({ error, fieldErrors, values });

  if (!fullName || !username || !email || !password) {
    return fail({
      full_name: fullName ? undefined : t.errorRequired,
      username: username ? undefined : t.errorRequired,
      email: email ? undefined : t.errorRequired,
      password: password ? undefined : t.errorRequired,
    });
  }

  let token: string;
  try {
    const data = await registerRequest(fullName, username, email, password);
    token = data.access_token;
  } catch (error) {
    if (error instanceof ApiError && error.code === "USERNAME_TAKEN") {
      return fail({ username: t.errorUsernameTaken });
    }
    if (error instanceof ApiError && error.code === "EMAIL_TAKEN") {
      return fail({ email: t.errorEmailTaken });
    }
    if (error instanceof ApiError && error.code === "WEAK_PASSWORD") {
      return fail({ password: t.errorWeakPassword });
    }
    // FastAPI request-validation failures (e.g. malformed email) are 422
    // and don't use the standard error envelope.
    if (error instanceof ApiError && error.status === 422) {
      return fail({ email: t.errorInvalidEmail });
    }
    return fail({}, t.errorGeneric);
  }

  await setSessionCookie(token);

  // Throws NEXT_REDIRECT — must run outside the try/catch above.
  redirect("/");
}

export type ForgotPasswordState = {
  /** Set once the request went through, so the form shows the success note. */
  sent: boolean;
  error: string | null;
};

/** Handle the "forgot my password" form (used with `useActionState`). */
export async function forgotPasswordAction(
  _prevState: ForgotPasswordState,
  formData: FormData,
): Promise<ForgotPasswordState> {
  const { dict } = await getServerI18n();
  const t = dict.forgotPassword;

  const email = String(formData.get("email") ?? "")
    .trim()
    .toLowerCase();

  if (!email) {
    return { sent: false, error: t.errorRequired };
  }

  try {
    await forgotPasswordRequest(email);
  } catch (error) {
    // A malformed email is a 422 from the backend validator.
    if (error instanceof ApiError && error.status === 422) {
      return { sent: false, error: t.errorInvalidEmail };
    }
    return { sent: false, error: t.errorGeneric };
  }

  return { sent: true, error: null };
}

export type ResetPasswordState = {
  done: boolean;
  error: string | null;
};

/** Handle the "set a new password" form (used with `useActionState`). */
export async function resetPasswordAction(
  _prevState: ResetPasswordState,
  formData: FormData,
): Promise<ResetPasswordState> {
  const { dict } = await getServerI18n();
  const t = dict.resetPassword;

  const token = String(formData.get("token") ?? "");
  const password = String(formData.get("password") ?? "");

  if (!token) {
    return { done: false, error: t.errorMissingToken };
  }
  if (!password) {
    return { done: false, error: t.errorRequired };
  }

  try {
    await resetPasswordRequest(token, password);
  } catch (error) {
    if (error instanceof ApiError && error.code === "INVALID_RESET_TOKEN") {
      return { done: false, error: t.errorInvalidToken };
    }
    if (error instanceof ApiError && error.code === "WEAK_PASSWORD") {
      return { done: false, error: t.errorWeakPassword };
    }
    return { done: false, error: t.errorGeneric };
  }

  return { done: true, error: null };
}

export type ChooseUsernameResult = { error: string | null };

/** Pick your own username (Google onboarding). Returns an error or null. */
export async function chooseUsernameAction(
  rawUsername: string,
): Promise<ChooseUsernameResult> {
  const { dict } = await getServerI18n();
  const t = dict.chooseUsername;

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value;
  if (!token) {
    return { error: t.errorGeneric };
  }

  const username = rawUsername.trim();
  if (!username) {
    return { error: t.errorRequired };
  }

  try {
    await chooseUsernameRequest(token, username);
  } catch (error) {
    if (error instanceof ApiError && error.code === "USERNAME_TAKEN") {
      return { error: t.errorTaken };
    }
    if (error instanceof ApiError && error.status === 422) {
      return { error: t.errorFormat };
    }
    return { error: t.errorGeneric };
  }

  return { error: null };
}

/** Clear the auth cookie and return to the landing page. */
export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_COOKIE_NAME);
  redirect("/");
}
