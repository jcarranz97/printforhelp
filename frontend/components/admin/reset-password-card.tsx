"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type ActionState, resetPasswordAction } from "@/actions/users.action";
import type { CurrentUser } from "@/lib/auth.api";

const initialState: ActionState = { error: null, success: false };

export function ResetPasswordCard({
  user,
  onClose,
}: {
  user: CurrentUser;
  onClose: () => void;
}) {
  const [state, formAction, pending] = useActionState(
    resetPasswordAction,
    initialState,
  );

  return (
    <Card variant="secondary">
      <Card.Header>
        <Card.Title>Cambiar contraseña de {user.username}</Card.Title>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-wrap items-end gap-3">
          <input type="hidden" name="userId" value={user.id} />
          <TextField
            name="new_password"
            type="text"
            isRequired
            className="min-w-64 flex-1"
          >
            <Label>Nueva contraseña</Label>
            <Input autoComplete="off" placeholder="Mín. 8, letra y número" />
          </TextField>
          <Button type="submit" isPending={pending}>
            Guardar
          </Button>
          <Button type="button" variant="ghost" onPress={onClose}>
            Cerrar
          </Button>
        </form>

        {state.error && (
          <Alert status="danger" className="mt-3">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>{state.error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
        {state.success && (
          <Alert status="success" className="mt-3">
            <Alert.Indicator />
            <Alert.Content>
              <Alert.Description>Contraseña actualizada.</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </Card.Content>
    </Card>
  );
}
