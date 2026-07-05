"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { buttonVariants } from "@heroui/styles";
import Link from "next/link";
import { useActionState } from "react";

import {
  type ResetPasswordState,
  resetPasswordAction,
} from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

const initialState: ResetPasswordState = { done: false, error: null };

export function ResetPasswordForm({ token }: { token: string }) {
  const { dict } = useI18n();
  const [state, formAction, pending] = useActionState(
    resetPasswordAction,
    initialState,
  );

  if (state.done) {
    return (
      <div className="flex flex-col gap-4">
        <Alert status="success">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Title>{dict.resetPassword.successTitle}</Alert.Title>
            <Alert.Description>
              {dict.resetPassword.successMessage}
            </Alert.Description>
          </Alert.Content>
        </Alert>
        <Link href="/login" className={buttonVariants({ className: "w-full" })}>
          {dict.resetPassword.goToLogin}
        </Link>
      </div>
    );
  }

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <input type="hidden" name="token" value={token} />

      <TextField name="password" type="password" isRequired>
        <Label>{dict.resetPassword.passwordLabel}</Label>
        <Input
          autoComplete="new-password"
          placeholder={dict.resetPassword.passwordPlaceholder}
        />
      </TextField>

      {state.error && (
        <Alert status="danger">
          <Alert.Indicator />
          <Alert.Content>
            <Alert.Description>{state.error}</Alert.Description>
          </Alert.Content>
        </Alert>
      )}

      <Button type="submit" isPending={pending} className="w-full">
        {pending ? dict.resetPassword.submitting : dict.resetPassword.submit}
      </Button>
    </form>
  );
}
