"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type UpdateSupplyState,
  updateSupplyAction,
} from "@/actions/supplies.action";
import { FileInput } from "@/components/forms/file-input";
import { TagInput } from "@/components/forms/tag-input";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";
import type { Supply } from "@/lib/supplies.api";

const initialState: UpdateSupplyState = { error: null };

/** Edit a supply's name, units, image, Markdown description, and tags. */
export function EditSupplyForm({
  supply,
  suggestions = [],
  unitSuggestions = [],
}: {
  supply: Supply;
  suggestions?: string[];
  unitSuggestions?: string[];
}) {
  const { dict } = useI18n();
  const t = dict.supplyForm;
  const action = updateSupplyAction.bind(null, supply.id);
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
            defaultValue={supply.name}
          >
            <Label>{t.name}</Label>
            <Input placeholder={t.namePlaceholder} />
          </TextField>

          <TagInput
            name="units"
            label={t.units}
            defaultTags={supply.units}
            suggestions={unitSuggestions}
          />
          <span className="-mt-2 text-xs text-muted">{t.unitsHint}</span>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.imageUpload}</span>
            {supply.image_url && (
              // External/stored image URL: a plain img avoids next/image
              // host allow-listing, matching the catalog cards.
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={supply.image_url}
                alt={t.currentImage}
                className="h-32 w-full rounded-xl object-cover"
              />
            )}
            <FileInput
              name="image_file"
              accept="image/png,image/jpeg,image/webp"
              chooseLabel={t.chooseFile}
              noFileLabel={t.noFile}
            />
            <span className="text-xs text-muted">{t.imageUploadHint}</span>
          </div>

          <TextField
            name="image_url"
            type="url"
            defaultValue={supply.image_url ?? ""}
          >
            <Label>{t.image}</Label>
            <Input placeholder={t.imagePlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={5}
              placeholder={t.descriptionPlaceholder}
              defaultValue={supply.description ?? ""}
            />
          </div>

          <TagInput
            name="tags"
            label={t.tags}
            defaultTags={supply.tags}
            suggestions={suggestions}
          />

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
