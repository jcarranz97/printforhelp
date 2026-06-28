"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  Label,
  ListBox,
  Select,
  TextField,
} from "@heroui/react";
import { useActionState, useEffect, useRef } from "react";

import { type ActionState, createUserAction } from "@/actions/users.action";

const initialState: ActionState = { error: null, success: false };

export function CreateUserForm() {
  const [state, formAction, pending] = useActionState(
    createUserAction,
    initialState,
  );
  const formRef = useRef<HTMLFormElement>(null);

  useEffect(() => {
    if (state.success) {
      formRef.current?.reset();
    }
  }, [state.success]);

  return (
    <Card>
      <Card.Header>
        <Card.Title>Crear cuenta</Card.Title>
        <Card.Description>
          Provisiona una cuenta para un colaborador de confianza.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <form ref={formRef} action={formAction} className="flex flex-col gap-4">
          <div className="grid gap-4 sm:grid-cols-3">
            <TextField name="username" type="text" isRequired>
              <Label>Usuario</Label>
              <Input autoComplete="off" placeholder="usuario" />
            </TextField>

            <TextField name="password" type="text" isRequired>
              <Label>Contraseña</Label>
              <Input autoComplete="off" placeholder="Mín. 8, letra y número" />
            </TextField>

            <Select
              name="role"
              defaultValue="user"
              placeholder="Selecciona un rol"
            >
              <Label>Rol</Label>
              <Select.Trigger>
                <Select.Value />
                <Select.Indicator />
              </Select.Trigger>
              <Select.Popover>
                <ListBox>
                  <ListBox.Item id="user" textValue="Usuario">
                    Usuario
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                  <ListBox.Item id="maintainer" textValue="Mantenedor">
                    Mantenedor
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                  <ListBox.Item id="admin" textValue="Administrador">
                    Administrador
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                </ListBox>
              </Select.Popover>
            </Select>
          </div>

          {state.error && (
            <Alert status="danger">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>{state.error}</Alert.Description>
              </Alert.Content>
            </Alert>
          )}
          {state.success && (
            <Alert status="success">
              <Alert.Indicator />
              <Alert.Content>
                <Alert.Description>
                  Cuenta creada correctamente.
                </Alert.Description>
              </Alert.Content>
            </Alert>
          )}

          <Button type="submit" isPending={pending} className="self-start">
            Crear cuenta
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
