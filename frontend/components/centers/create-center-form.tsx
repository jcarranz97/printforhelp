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
import { useI18n } from "@/i18n/provider";

const initialState: CreateCenterState = { error: null };

export function CreateCenterForm() {
  const { dict } = useI18n();
  const t = dict.centerForm;
  const [state, formAction, pending] = useActionState(
    createCenterAction,
    initialState,
  );

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.title}</Card.Title>
        <Card.Description>{t.description}</Card.Description>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-col gap-4">
          <TextField name="name" type="text" isRequired>
            <Label>{t.name}</Label>
            <Input placeholder={t.namePlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField name="country" type="text" isRequired>
              <Label>{t.country}</Label>
              <Input placeholder={t.countryPlaceholder} />
            </TextField>
            <TextField name="city" type="text" isRequired>
              <Label>{t.city}</Label>
              <Input placeholder={t.cityPlaceholder} />
            </TextField>
          </div>

          <TextField name="address" isRequired>
            <Label>{t.address}</Label>
            <TextArea rows={2} placeholder={t.addressPlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField name="contact" type="text" isRequired>
              <Label>{t.contact}</Label>
              <Input placeholder={t.contactPlaceholder} />
            </TextField>
            <TextField name="opening_hours" type="text">
              <Label>{t.hours}</Label>
              <Input placeholder={t.hoursPlaceholder} />
            </TextField>
          </div>

          <TextField name="notes">
            <Label>{t.notes}</Label>
            <TextArea rows={3} placeholder={t.notesPlaceholder} />
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
            {t.submit}
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
