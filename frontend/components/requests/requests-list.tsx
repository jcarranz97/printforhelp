"use client";

import { Card, Chip } from "@heroui/react";
import Link from "next/link";

import { useI18n } from "@/i18n/provider";
import type { RequestStatus, RequestSummary } from "@/lib/requests.api";

const STATUS_COLOR: Record<RequestStatus, "success" | "default" | "warning"> = {
  open: "success",
  fulfilled: "default",
  closed: "warning",
};

/** Public list of campaigns (Requests) as a responsive grid of cards. */
export function RequestsList({ requests }: { requests: RequestSummary[] }) {
  const { dict } = useI18n();
  const t = dict.requests;

  if (requests.length === 0) {
    return (
      <Card variant="transparent" className="py-12 text-center">
        <Card.Content>
          <p className="text-muted">{t.empty}</p>
        </Card.Content>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {requests.map((request) => (
        <Link
          key={request.id}
          href={`/requests/${request.id}`}
          className="rounded-2xl transition-shadow hover:shadow-md"
          aria-label={`${t.viewDetails} ${request.title}`}
        >
          <Card className="h-full">
            <Card.Header>
              <Card.Title>{request.title}</Card.Title>
              {request.description && (
                <Card.Description>{request.description}</Card.Description>
              )}
            </Card.Header>
            <Card.Footer>
              <Chip
                color={STATUS_COLOR[request.status]}
                variant="soft"
                size="sm"
              >
                {t.status[request.status]}
              </Chip>
            </Card.Footer>
          </Card>
        </Link>
      ))}
    </div>
  );
}
