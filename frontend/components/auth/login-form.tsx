"use client";

import { Alert, Button, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type LoginState, loginAction } from "@/actions/auth.action";

const initialState: LoginState = { error: null };

export function LoginForm() {
  const [state, formAction, pending] = useActionState(
    loginAction,
    initialState,
  );

  return (
    <form action={formAction} className="flex flex-col gap-4">
      <TextField name="username" type="text" isRequired>
        <Label>Usuario</Label>
        <Input autoComplete="username" placeholder="Tu usuario" />
      </TextField>

      <TextField name="password" type="password" isRequired>
        <Label>Contraseña</Label>
        <Input autoComplete="current-password" placeholder="Tu contraseña" />
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
        {pending ? "Entrando…" : "Iniciar sesión"}
      </Button>
    </form>
  );
}
