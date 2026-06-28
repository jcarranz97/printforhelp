"use client";

import {
  Alert,
  Button,
  Card,
  Input,
  Label,
  TextArea,
  TextField,
} from "@heroui/react";
import { useActionState } from "react";

import {
  type CreateCenterState,
  createCenterAction,
} from "@/actions/collection-centers.action";

const initialState: CreateCenterState = { error: null };

export function CreateCenterForm() {
  const [state, formAction, pending] = useActionState(
    createCenterAction,
    initialState,
  );

  return (
    <Card>
      <Card.Header>
        <Card.Title>Registrar centro de acopio</Card.Title>
        <Card.Description>
          Tu centro aparecerá de inmediato en el directorio como «No verificado»
          hasta que un mantenedor lo verifique.
        </Card.Description>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-col gap-4">
          <TextField name="name" type="text" isRequired>
            <Label>Nombre</Label>
            <Input placeholder="UCAB Lab — Caracas" />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField name="country" type="text" isRequired>
              <Label>País</Label>
              <Input placeholder="VE" />
            </TextField>
            <TextField name="city" type="text" isRequired>
              <Label>Ciudad</Label>
              <Input placeholder="Caracas" />
            </TextField>
          </div>

          <TextField name="address" isRequired>
            <Label>Dirección</Label>
            <TextArea rows={2} placeholder="Av. Teherán, Montalbán, Caracas" />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField name="contact" type="text" isRequired>
              <Label>Contacto</Label>
              <Input placeholder="Teléfono o correo" />
            </TextField>
            <TextField name="opening_hours" type="text">
              <Label>Horario (opcional)</Label>
              <Input placeholder="Lun-Vie 9-17" />
            </TextField>
          </div>

          <TextField name="notes">
            <Label>Notas (opcional)</Label>
            <TextArea
              rows={3}
              placeholder="Indicaciones de entrega, referencias, etc."
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

          <Button type="submit" isPending={pending} className="self-start">
            Registrar centro
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
