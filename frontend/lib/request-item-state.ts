import type { HelpState, RequestItem } from "@/lib/requests.api";

/**
 * Bucket one item by whether it still needs help. Mirrors the backend
 * `compute_item_help_state`: a fulfilled/closed item is `completed`; an open
 * item with enough committed is `committed`; otherwise it still `needs_help`.
 */
export function deriveItemState(item: RequestItem): HelpState {
  if (item.status === "fulfilled" || item.status === "closed") {
    return "completed";
  }
  const target = item.progress.target_quantity;
  if (target !== null && item.progress.committed_quantity >= target) {
    return "committed";
  }
  return "needs_help";
}
