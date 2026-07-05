"use client";

import {
  Alert,
  Button,
  FieldError,
  Input,
  Label,
  TextField,
} from "@heroui/react";
import { useActionState, useEffect, useState } from "react";

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

  // Field errors come from the last submission. Once the user edits a field
  // we hide its error so a stale "already taken" doesn't linger after they
  // type something new. A fresh submission result resets this.
  const [edited, setEdited] = useState<Record<string, boolean>>({});
  useEffect(() => {
    setEdited({});
  }, [state]);
  const errorFor = (name: keyof typeof fieldErrors): string | undefined =>
    edited[name] ? undefined : fieldErrors[name];
  const markEdited = (name: string) =>
    setEdited((prev) => (prev[name] ? prev : { ...prev, [name]: true }));

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <TextField
        name="full_name"
        type="text"
        isRequired
        isInvalid={Boolean(errorFor("full_name"))}
        defaultValue={values.full_name}
        onChange={() => markEdited("full_name")}
      >
        <Label>{dict.register.nameLabel}</Label>
        <Input
          autoComplete="name"
          placeholder={dict.register.namePlaceholder}
        />
        {errorFor("full_name") && (
          <FieldError>{errorFor("full_name")}</FieldError>
        )}
      </TextField>

      <TextField
        name="username"
        type="text"
        isRequired
        isInvalid={Boolean(errorFor("username"))}
        defaultValue={values.username}
        onChange={() => markEdited("username")}
      >
        <Label>{dict.register.usernameLabel}</Label>
        <Input
          autoComplete="username"
          placeholder={dict.register.usernamePlaceholder}
        />
        {errorFor("username") ? (
          <FieldError>{errorFor("username")}</FieldError>
        ) : (
          <p className="text-xs text-muted">{dict.register.usernameHint}</p>
        )}
      </TextField>

      <TextField
        name="email"
        type="email"
        isRequired
        isInvalid={Boolean(errorFor("email"))}
        defaultValue={values.email}
        onChange={() => markEdited("email")}
      >
        <Label>{dict.register.emailLabel}</Label>
        <Input
          autoComplete="email"
          placeholder={dict.register.emailPlaceholder}
        />
        {errorFor("email") && <FieldError>{errorFor("email")}</FieldError>}
      </TextField>

      <TextField
        name="password"
        type="password"
        isRequired
        isInvalid={Boolean(errorFor("password"))}
        onChange={() => markEdited("password")}
      >
        <Label>{dict.register.passwordLabel}</Label>
        <Input
          autoComplete="new-password"
          placeholder={dict.register.passwordPlaceholder}
        />
        {errorFor("password") && (
          <FieldError>{errorFor("password")}</FieldError>
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
