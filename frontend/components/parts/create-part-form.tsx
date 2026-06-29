"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import { type CreatePartState, createPartAction } from "@/actions/parts.action";
import { FileInput } from "@/components/forms/file-input";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
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

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.sourceFile}</span>
            <FileInput
              name="source_file"
              accept=".stl,.3mf,.obj,.step,.stp,.gcode,.ply,.amf,.scad,.f3d,.zip,.7z,.rar"
              chooseLabel={t.chooseFile}
              noFileLabel={t.noFile}
            />
            <span className="text-xs text-muted">{t.sourceFileHint}</span>
          </div>

          <TextField name="source_url" type="url">
            <Label>{t.sourceUrl}</Label>
            <Input placeholder={t.sourceUrlPlaceholder} />
          </TextField>

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
