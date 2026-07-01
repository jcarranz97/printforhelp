"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type UpdatePartState, updatePartAction } from "@/actions/parts.action";
import { FileInput } from "@/components/forms/file-input";
import { TagInput } from "@/components/forms/tag-input";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";
import type { Part } from "@/lib/parts.api";

const initialState: UpdatePartState = { error: null };

/** Edit a Part's name, links, Markdown description, and tags. */
export function EditPartForm({
  part,
  suggestions = [],
}: {
  part: Part;
  suggestions?: string[];
}) {
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

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.sourceFile}</span>
            {part.source_url && (
              <a
                href={part.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted underline"
              >
                {t.currentFile}
              </a>
            )}
            <FileInput
              name="source_file"
              accept=".stl,.3mf,.obj,.step,.stp,.gcode,.ply,.amf,.scad,.f3d,.zip,.7z,.rar"
              chooseLabel={t.chooseFile}
              noFileLabel={t.noFile}
            />
            <span className="text-xs text-muted">{t.sourceFileHint}</span>
          </div>

          <TextField
            name="source_url"
            type="url"
            defaultValue={part.source_url ?? ""}
          >
            <Label>{t.sourceUrl}</Label>
            <Input placeholder={t.sourceUrlPlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.imageUpload}</span>
            {part.image_url && (
              // External/stored image URL: a plain img avoids next/image
              // host allow-listing, matching the catalog cards.
              <img
                src={part.image_url}
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
            defaultValue={part.image_url ?? ""}
          >
            <Label>{t.image}</Label>
            <Input placeholder={t.imagePlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.labelUpload}</span>
            {part.label_image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={part.label_image_url}
                alt={t.currentLabel}
                className="h-24 w-full rounded-xl object-contain"
              />
            )}
            <FileInput
              name="label_file"
              accept="image/png,image/jpeg,image/webp"
              chooseLabel={t.chooseFile}
              noFileLabel={t.noFile}
            />
            <span className="text-xs text-muted">{t.labelUploadHint}</span>
          </div>

          <TextField
            name="label_image_url"
            type="url"
            defaultValue={part.label_image_url ?? ""}
          >
            <Label>{t.label}</Label>
            <Input placeholder={t.labelPlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={5}
              placeholder={t.descriptionPlaceholder}
              defaultValue={part.description ?? ""}
            />
          </div>

          <TagInput
            name="tags"
            label={t.tags}
            defaultTags={part.tags}
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
