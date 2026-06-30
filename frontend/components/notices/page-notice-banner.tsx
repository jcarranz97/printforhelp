import { type Notice, listPageNotices } from "@/lib/notices.api";

import { NoticeBannerList } from "./notice-banner-list";

/**
 * Global page-banner strip rendered under the top nav on every page. Fetches
 * all approved page notices once; the client list filters them by route.
 */
export async function PageNoticeBanner() {
  let notices: Notice[] = [];
  try {
    notices = await listPageNotices();
  } catch {
    // Never let a banner outage break the page shell.
    return null;
  }
  if (notices.length === 0) {
    return null;
  }
  return <NoticeBannerList notices={notices} mode="page" />;
}
