"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type UpdateRequestState,
  updateRequestAction,
} from "@/actions/requests.action";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { PreferredCentersField } from "@/components/requests/preferred-centers-field";
import { RequestImageField } from "@/components/requests/request-image-field";
import { useI18n } from "@/i18n/provider";
import type { CenterOption } from "@/components/requests/preferred-centers-field";
import type { RequestDetail } from "@/lib/requests.api";

const initialState: UpdateRequestState = { error: null };

/** Edit a campaign's title, description, deadline, and preferred centers. */
export function EditRequestForm({
  request,
  centers,
}: {
  request: RequestDetail;
  centers: CenterOption[];
}) {
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

          <RequestImageField
            defaultUrl={request.image_url ?? ""}
            defaultFocusX={request.image_focus_x}
            defaultFocusY={request.image_focus_y}
          />

          <TextField
            name="deadline"
            type="date"
            defaultValue={request.deadline ?? ""}
          >
            <Label>{t.deadline}</Label>
            <Input />
          </TextField>

          <PreferredCentersField
            centers={centers}
            defaultSelectedIds={request.preferred_collection_center_ids}
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
