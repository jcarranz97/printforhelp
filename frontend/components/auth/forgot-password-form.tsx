"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type ForgotPasswordState,
  forgotPasswordAction,
} from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

const initialState: ForgotPasswordState = { sent: false, error: null };

export function ForgotPasswordForm() {
  const { dict } = useI18n();
  const [state, formAction, pending] = useActionState(
    forgotPasswordAction,
    initialState,
  );

  if (state.sent) {
    return (
      <Alert status="success">
        <Alert.Indicator />
        <Alert.Content>
          <Alert.Title>{dict.forgotPassword.successTitle}</Alert.Title>
          <Alert.Description>
            {dict.forgotPassword.successMessage}
          </Alert.Description>
        </Alert.Content>
      </Alert>
    );
  }

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <TextField name="email" type="email" isRequired>
        <Label>{dict.forgotPassword.emailLabel}</Label>
        <Input
          autoComplete="email"
          placeholder={dict.forgotPassword.emailPlaceholder}
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
        {pending ? dict.forgotPassword.submitting : dict.forgotPassword.submit}
      </Button>
    </form>
  );
}
