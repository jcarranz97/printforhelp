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
  type UpdateCenterState,
  updateCenterAction,
} from "@/actions/collection-centers.action";
import { useI18n } from "@/i18n/provider";
import type { CollectionCenter } from "@/lib/collection-centers.api";

const initialState: UpdateCenterState = { error: null };

/**
 * Edit form for an existing collection center. Mirrors the create form but
 * pre-fills every field from the current center and submits to the bound
 * `updateCenterAction`. Authorization is re-checked server-side (NFR-006).
 */
export function EditCenterForm({ center }: { center: CollectionCenter }) {
  const { dict } = useI18n();
  const t = dict.centerForm;
  const action = updateCenterAction.bind(null, center.id);
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.editTitle}</Card.Title>
        <Card.Description>{t.editDescription}</Card.Description>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-col gap-4">
          <TextField
            name="name"
            type="text"
            isRequired
            defaultValue={center.name}
          >
            <Label>{t.name}</Label>
            <Input placeholder={t.namePlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              name="country"
              type="text"
              isRequired
              defaultValue={center.country}
            >
              <Label>{t.country}</Label>
              <Input placeholder={t.countryPlaceholder} />
            </TextField>
            <TextField
              name="city"
              type="text"
              isRequired
              defaultValue={center.city}
            >
              <Label>{t.city}</Label>
              <Input placeholder={t.cityPlaceholder} />
            </TextField>
          </div>

          <TextField name="address" isRequired defaultValue={center.address}>
            <Label>{t.address}</Label>
            <TextArea rows={2} placeholder={t.addressPlaceholder} />
          </TextField>

          <div className="grid gap-4 sm:grid-cols-2">
            <TextField
              name="contact"
              type="text"
              isRequired
              defaultValue={center.contact}
            >
              <Label>{t.contact}</Label>
              <Input placeholder={t.contactPlaceholder} />
            </TextField>
            <TextField
              name="opening_hours"
              type="text"
              defaultValue={center.opening_hours ?? ""}
            >
              <Label>{t.hours}</Label>
              <Input placeholder={t.hoursPlaceholder} />
            </TextField>
          </div>

          <TextField name="notes" defaultValue={center.notes ?? ""}>
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
            {t.editSubmit}
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
