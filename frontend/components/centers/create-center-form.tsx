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

/**
 * Optional pre-fill values used when cloning an existing center. Every
 * field is optional so the same form serves a blank registration and a
 * pre-populated clone.
 */
export type CenterFormValues = {
  name?: string;
  country?: string;
  city?: string;
  address?: string;
  location_url?: string;
  contact?: string;
  opening_hours?: string;
  description?: string;
};

export function CreateCenterForm({
  initialValues,
}: {
  initialValues?: CenterFormValues;
}) {
  const { dict } = useI18n();
  const t = dict.centerForm;
  const v = initialValues ?? {};
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
          <TextField name="name" type="text" isRequired defaultValue={v.name}>
            <Label>{t.name}</Label>
            <Input placeholder={t.namePlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              name="country"
              type="text"
              isRequired
              defaultValue={v.country}
            >
              <Label>{t.country}</Label>
              <Input placeholder={t.countryPlaceholder} />
            </TextField>
            <TextField name="city" type="text" isRequired defaultValue={v.city}>
              <Label>{t.city}</Label>
              <Input placeholder={t.cityPlaceholder} />
            </TextField>
          </div>

          <TextField name="address" isRequired defaultValue={v.address}>
            <Label>{t.address}</Label>
            <TextArea rows={2} placeholder={t.addressPlaceholder} />
          </TextField>

          <TextField
            name="location_url"
            type="url"
            defaultValue={v.location_url}
          >
            <Label>{t.locationUrl}</Label>
            <Input placeholder={t.locationUrlPlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              name="contact"
              type="text"
              isRequired
              defaultValue={v.contact}
            >
              <Label>{t.contact}</Label>
              <Input placeholder={t.contactPlaceholder} />
            </TextField>
            <TextField
              name="opening_hours"
              type="text"
              defaultValue={v.opening_hours}
            >
              <Label>{t.hours}</Label>
              <Input placeholder={t.hoursPlaceholder} />
            </TextField>
          </div>

          <TextField name="description" defaultValue={v.description}>
            <Label>{t.descriptionLabel}</Label>
            <TextArea rows={4} placeholder={t.descriptionPlaceholder} />
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
