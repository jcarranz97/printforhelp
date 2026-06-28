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

import { type CreatePartState, createPartAction } from "@/actions/parts.action";
import { useI18n } from "@/i18n/provider";

const initialState: CreatePartState = { error: null };

export function CreatePartForm() {
  const { dict } = useI18n();
  const t = dict.partForm;
  const [state, formAction, pending] = useActionState(
    createPartAction,
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

          <TextField name="source_url" type="url" isRequired>
            <Label>{t.sourceUrl}</Label>
            <Input placeholder={t.sourceUrlPlaceholder} />
          </TextField>

          <TextField name="image_url" type="url">
            <Label>{t.image}</Label>
            <Input placeholder={t.imagePlaceholder} />
          </TextField>

          <TextField name="description">
            <Label>{t.descriptionLabel}</Label>
            <TextArea rows={3} placeholder={t.descriptionPlaceholder} />
          </TextField>

          <TextField name="tags" type="text">
            <Label>{t.tags}</Label>
            <Input placeholder={t.tagsPlaceholder} />
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
