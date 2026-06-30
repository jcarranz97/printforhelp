/** Shared display helpers for the admin notice components. */

import type { Dictionary } from "@/i18n/dictionaries";
import type { Notice, NoticeSeverity, NoticeStatus } from "@/lib/notices.api";

export function severityChipColor(
  severity: NoticeSeverity,
): "default" | "warning" | "danger" {
  if (severity === "critical") {
    return "danger";
  }
  if (severity === "warning") {
    return "warning";
  }
  return "default";
}

export function severityLabel(
  severity: NoticeSeverity,
  t: Dictionary["notices"],
): string {
  if (severity === "critical") {
    return t.severityCritical;
  }
  if (severity === "warning") {
    return t.severityWarning;
  }
  return t.severityInfo;
}

export function statusLabel(
  status: NoticeStatus,
  t: Dictionary["notices"],
): string {
  if (status === "approved") {
    return t.statusApproved;
  }
  if (status === "declined") {
    return t.statusDeclined;
  }
  return t.statusPending;
}

export function statusChipColor(
  status: NoticeStatus,
): "success" | "danger" | "warning" {
  if (status === "approved") {
    return "success";
  }
  if (status === "declined") {
    return "danger";
  }
  return "warning";
}

/** Human label for a notice's scope: an entity kind, or "Pages". */
export function targetLabel(notice: Notice, t: Dictionary["notices"]): string {
  if (notice.target_type === "resource") {
    return t.targetResource;
  }
  if (notice.target_type === "collection_center") {
    return t.targetCollectionCenter;
  }
  if (notice.target_type === "request") {
    return t.targetRequest;
  }
  return t.targetPage;
}
