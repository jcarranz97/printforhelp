import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CreatePageNoticeForm } from "@/components/admin/notices/create-page-notice-form";
import { NoticeQueue } from "@/components/admin/notices/notice-queue";
import { NoticesTable } from "@/components/admin/notices/notices-table";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listManageNotices } from "@/lib/notices.api";

export default async function AdminNoticesPage() {
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    redirect("/login?next=/admin/notices");
  }
  if (currentUser.role !== "admin" && currentUser.role !== "maintainer") {
    redirect("/");
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value ?? "";
  const notices = await listManageNotices(token);
  const { dict } = await getServerI18n();

  const pending = notices.filter((notice) => notice.status === "pending");
  const reviewed = notices.filter((notice) => notice.status !== "pending");

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{dict.notices.pageTitle}</h1>
        <p className="mt-1 text-sm text-muted">{dict.notices.pageSubtitle}</p>
      </div>

      <div className="flex flex-col gap-10">
        <NoticeQueue notices={pending} />
        <CreatePageNoticeForm />
        <NoticesTable notices={reviewed} />
      </div>
    </main>
  );
}
