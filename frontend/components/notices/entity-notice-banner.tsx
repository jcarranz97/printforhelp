import {
  type Notice,
  type NoticeTargetType,
  listEntityNotices,
} from "@/lib/notices.api";

import { NoticeBannerList } from "./notice-banner-list";

/**
 * Banner strip for a single entity's detail page (a part, center, or
 * request). Renders the approved notices attached to that entity.
 */
export async function EntityNoticeBanner({
  targetType,
  targetId,
}: {
  targetType: NoticeTargetType;
  targetId: string;
}) {
  let notices: Notice[] = [];
  try {
    notices = await listEntityNotices(targetType, targetId);
  } catch {
    return null;
  }
  if (notices.length === 0) {
    return null;
  }
  return <NoticeBannerList notices={notices} mode="entity" />;
}
