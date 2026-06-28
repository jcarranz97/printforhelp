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

import { type UpdatePartState, updatePartAction } from "@/actions/parts.action";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";

const initialState: UpdatePartState = { error: null };

/** Edit a Part's name, links, Markdown description, and tags. */
export function EditPartForm({ part }: { part: Part }) {
  const { dict } = useI18n();
  const t = dict.partForm;
  const action = updatePartAction.bind(null, part.id);
  const [state, formAction, pending] = useActionState(action, initialState);

  return (
    <Card>
      <Card.Header>
        <Card.Title>{t.editTitle}</Card.Title>
        <Card.Description>{t.description}</Card.Description>
      </Card.Header>
      <Card.Content>
        <form action={formAction} className="flex flex-col gap-4">
          <TextField
            name="name"
            type="text"
            isRequired
            defaultValue={part.name}
          >
            <Label>{t.name}</Label>
            <Input placeholder={t.namePlaceholder} />
          </TextField>

          <TextField
            name="source_url"
            type="url"
            isRequired
            defaultValue={part.source_url}
          >
            <Label>{t.sourceUrl}</Label>
            <Input placeholder={t.sourceUrlPlaceholder} />
          </TextField>

          <TextField
            name="image_url"
            type="url"
            defaultValue={part.image_url ?? ""}
          >
            <Label>{t.image}</Label>
            <Input placeholder={t.imagePlaceholder} />
          </TextField>

          <TextField name="description" defaultValue={part.description ?? ""}>
            <Label>{t.descriptionLabel}</Label>
            <TextArea rows={5} placeholder={t.descriptionPlaceholder} />
          </TextField>

          <TextField
            name="tags"
            type="text"
            defaultValue={part.tags.join(", ")}
          >
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
            {t.editSubmit}
          </Button>
        </form>
      </Card.Content>
    </Card>
  );
}
