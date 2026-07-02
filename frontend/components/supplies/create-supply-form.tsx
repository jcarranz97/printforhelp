"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type CreateSupplyState,
  createSupplyAction,
} from "@/actions/supplies.action";
import { FileInput } from "@/components/forms/file-input";
import { TagInput } from "@/components/forms/tag-input";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";

const initialState: CreateSupplyState = { error: null };

/** Register a supply: name, optional image, units of measure, description, tags. */
export function CreateSupplyForm({
  suggestions = [],
  unitSuggestions = [],
}: {
  suggestions?: string[];
  unitSuggestions?: string[];
}) {
  const { dict } = useI18n();
  const t = dict.supplyForm;
  const [state, formAction, pending] = useActionState(
    createSupplyAction,
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

          <TagInput
            name="units"
            label={t.units}
            suggestions={unitSuggestions}
          />
          <span className="-mt-2 text-xs text-muted">{t.unitsHint}</span>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.imageUpload}</span>
            <FileInput
              name="image_file"
              accept="image/png,image/jpeg,image/webp"
              chooseLabel={t.chooseFile}
              noFileLabel={t.noFile}
            />
            <span className="text-xs text-muted">{t.imageUploadHint}</span>
          </div>

          <TextField name="image_url" type="url">
            <Label>{t.image}</Label>
            <Input placeholder={t.imagePlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={4}
              placeholder={t.descriptionPlaceholder}
            />
          </div>

          <TagInput name="tags" label={t.tags} suggestions={suggestions} />

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
