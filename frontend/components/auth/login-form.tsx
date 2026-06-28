"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type LoginState, loginAction } from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

const initialState: LoginState = { error: null };

export function LoginForm() {
  const { dict } = useI18n();
  const [state, formAction, pending] = useActionState(
    loginAction,
    initialState,
  );

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <TextField name="username" type="text" isRequired>
        <Label>{dict.login.usernameLabel}</Label>
        <Input
          autoComplete="username"
          placeholder={dict.login.usernamePlaceholder}
        />
      </TextField>

      <TextField name="password" type="password" isRequired>
        <Label>{dict.login.passwordLabel}</Label>
        <Input
          autoComplete="current-password"
          placeholder={dict.login.passwordPlaceholder}
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
        {pending ? dict.login.submitting : dict.login.submit}
      </Button>
    </form>
  );
}
