import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { getCurrentUser } from "@/actions/auth.action";
import { CreateUserForm } from "@/components/admin/create-user-form";
import { UsersTable } from "@/components/admin/users-table";
import { getServerI18n } from "@/i18n/server";
import { AUTH_COOKIE_NAME } from "@/lib/api";
import { listUsers } from "@/lib/users.api";

export default async function AdminUsersPage() {
  const currentUser = await getCurrentUser();
  if (!currentUser) {
    redirect("/login?next=/admin/users");
  }
  if (currentUser.role !== "admin") {
    redirect("/");
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(AUTH_COOKIE_NAME)?.value ?? "";
  const users = await listUsers(token);
  const { dict } = await getServerI18n();

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8">
        <h1 className="text-2xl font-bold">{dict.admin.pageTitle}</h1>
        <p className="mt-1 text-sm text-muted">{dict.admin.pageSubtitle}</p>
      </div>

      <div className="flex flex-col gap-8">
        <CreateUserForm />
        <UsersTable users={users} currentUserId={currentUser.id} />
      </div>
    </main>
  );
}
