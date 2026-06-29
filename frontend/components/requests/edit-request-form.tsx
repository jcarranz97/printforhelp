"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type UpdateRequestState,
  updateRequestAction,
} from "@/actions/requests.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { useI18n } from "@/i18n/provider";
import type { RequestDetail } from "@/lib/requests.api";

const initialState: UpdateRequestState = { error: null };

/** Edit a campaign's title, Markdown description, and deadline (FR-042). */
export function EditRequestForm({ request }: { request: RequestDetail }) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const action = updateRequestAction.bind(null, request.id);
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
            name="title"
            type="text"
            isRequired
            defaultValue={request.title}
          >
            <Label>{t.campaignTitle}</Label>
            <Input placeholder={t.campaignTitlePlaceholder} />
          </TextField>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={5}
              placeholder={t.descriptionPlaceholder}
              defaultValue={request.description ?? ""}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.imageUpload}</span>
            {request.image_url && (
              // External/stored image URL: a plain img avoids next/image
              // host allow-listing, matching the rest of the app.
              <img
                src={request.image_url}
                alt={t.currentImage}
                className="h-32 w-full rounded-xl object-cover"
              />
            )}
            <input
              type="file"
              name="image_file"
              accept="image/png,image/jpeg,image/webp"
              className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-default-100 file:px-3 file:py-1.5 file:text-sm file:font-medium"
            />
            <span className="text-xs text-muted">{t.imageUploadHint}</span>
          </div>

          <TextField
            name="image_url"
            type="url"
            defaultValue={request.image_url ?? ""}
          >
            <Label>{t.imageUrl}</Label>
            <Input placeholder={t.imageUrlPlaceholder} />
          </TextField>

          <TextField
            name="deadline"
            type="date"
            defaultValue={request.deadline ?? ""}
          >
            <Label>{t.deadline}</Label>
            <Input />
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
