import { useEffect, useState } from "react";
import { apiFetch } from "../api/client";

interface AdminUser {
  id: number;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
}

export default function Admin() {
  const [users, setUsers] = useState<AdminUser[]>([]);

  useEffect(() => {
    apiFetch<AdminUser[]>("/admin/users").then(setUsers);
  }, []);

  async function toggle(u: AdminUser) {
    await apiFetch(`/admin/users/${u.id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: !u.is_active }),
    });
    setUsers((us) => us.map((x) => (x.id === u.id ? { ...x, is_active: !x.is_active } : x)));
  }

  async function resetPassword(u: AdminUser) {
    const pw = prompt(`New password for ${u.username}:`);
    if (!pw) return;
    await apiFetch(`/admin/users/${u.id}/reset-password`, {
      method: "POST",
      body: JSON.stringify({ new_password: pw }),
    });
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h2 className="text-2xl font-bold">Admin</h2>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-slate-400">
            <th className="p-2">User</th>
            <th>Role</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id} className="border-b border-slate-800">
              <td className="p-2">
                {u.username}
                <div className="text-xs text-slate-500">{u.email}</div>
              </td>
              <td>{u.role}</td>
              <td>{u.is_active ? "Active" : "Disabled"}</td>
              <td className="space-x-2">
                <button className="text-amber-400" onClick={() => toggle(u)}>
                  {u.is_active ? "Disable" : "Enable"}
                </button>
                <button className="text-slate-400" onClick={() => resetPassword(u)}>
                  Reset pwd
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
