"use client";

import { Alert, Button, Card, Input, Label, TextField } from "@heroui/react";
import { useActionState } from "react";

import {
  type CreateRequestState,
  createRequestAction,
} from "@/actions/requests.action";
import { BeneficiaryField } from "@/components/requests/beneficiary-field";
import { MarkdownEditor } from "@/components/markdown/markdown-editor";
import { PreferredCentersField } from "@/components/requests/preferred-centers-field";
import { RequestImageField } from "@/components/requests/request-image-field";
import { useI18n } from "@/i18n/provider";
import type { CenterOption } from "@/components/requests/preferred-centers-field";

const initialState: CreateRequestState = { error: null };

/**
 * Create-campaign form: title, description, cover image, deadline, and
 * optional preferred drop-off centers. Items (parts / supplies) are added
 * afterwards from the request page, so they are intentionally not asked for
 * here (a request may start empty, FR-038).
 */
export function CreateRequestForm({
  centers,
  beneficiarySuggestions,
}: {
  centers: CenterOption[];
  beneficiarySuggestions: string[];
}) {
  const { dict } = useI18n();
  const t = dict.requestForm;
  const [state, formAction, pending] = useActionState(
    createRequestAction,
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
          <TextField name="title" type="text" isRequired>
            <Label>{t.campaignTitle}</Label>
            <Input placeholder={t.campaignTitlePlaceholder} />
          </TextField>

          <BeneficiaryField suggestions={beneficiarySuggestions} />

          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">{t.descriptionLabel}</span>
            <MarkdownEditor
              name="description"
              rows={3}
              placeholder={t.descriptionPlaceholder}
              showImageHint={false}
            />
          </div>

          <RequestImageField />

          <TextField name="deadline" type="date">
            <Label>{t.deadline}</Label>
            <Input />
          </TextField>

          <PreferredCentersField centers={centers} />

          <p className="text-xs text-muted">{t.afterCreateHint}</p>

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
