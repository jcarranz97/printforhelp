"use client";

import {
  Alert,
  Button,
  FieldError,
  Input,
  Label,
  TextField,
} from "@heroui/react";
import { useActionState } from "react";

import { type RegisterState, registerAction } from "@/actions/auth.action";
import { useI18n } from "@/i18n/provider";

const initialState: RegisterState = {
  error: null,
  fieldErrors: {},
  values: { full_name: "", username: "", email: "" },
};

export function RegisterForm() {
  const { dict } = useI18n();
  const [state, formAction, pending] = useActionState(
    registerAction,
    initialState,
  );
  const { fieldErrors, values } = state;

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <TextField
        name="full_name"
        type="text"
        isRequired
        isInvalid={Boolean(fieldErrors.full_name)}
        defaultValue={values.full_name}
      >
        <Label>{dict.register.nameLabel}</Label>
        <Input
          autoComplete="name"
          placeholder={dict.register.namePlaceholder}
        />
        {fieldErrors.full_name && (
          <FieldError>{fieldErrors.full_name}</FieldError>
        )}
      </TextField>

      <TextField
        name="username"
        type="text"
        isRequired
        isInvalid={Boolean(fieldErrors.username)}
        defaultValue={values.username}
      >
        <Label>{dict.register.usernameLabel}</Label>
        <Input
          autoComplete="username"
          placeholder={dict.register.usernamePlaceholder}
        />
        {fieldErrors.username && (
          <FieldError>{fieldErrors.username}</FieldError>
        )}
      </TextField>

      <TextField
        name="email"
        type="email"
        isRequired
        isInvalid={Boolean(fieldErrors.email)}
        defaultValue={values.email}
      >
        <Label>{dict.register.emailLabel}</Label>
        <Input
          autoComplete="email"
          placeholder={dict.register.emailPlaceholder}
        />
        {fieldErrors.email && <FieldError>{fieldErrors.email}</FieldError>}
      </TextField>

      <TextField
        name="password"
        type="password"
        isRequired
        isInvalid={Boolean(fieldErrors.password)}
      >
        <Label>{dict.register.passwordLabel}</Label>
        <Input
          autoComplete="new-password"
          placeholder={dict.register.passwordPlaceholder}
        />
        {fieldErrors.password && (
          <FieldError>{fieldErrors.password}</FieldError>
        )}
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
        {pending ? dict.register.submitting : dict.register.submit}
      </Button>
    </form>
  );
}
