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
  type UpdateRequestState,
  updateRequestAction,
} from "@/actions/requests.action";
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

          <TextField
            name="description"
            defaultValue={request.description ?? ""}
          >
            <Label>{t.descriptionLabel}</Label>
            <TextArea rows={5} placeholder={t.descriptionPlaceholder} />
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
