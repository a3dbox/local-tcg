import { useEffect, useState, useCallback } from "react";
import { Navigate } from "react-router-dom";
import { Pencil, Trash2, UserPlus, Shield } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr, gbp } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageTitle, Spinner, Btn } from "@/components/UI";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

const input = "w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-[#E3350D]";

function UserForm({ open, initial, onClose, onSaved }) {
  const isNew = !initial?.id;
  const [f, setF] = useState({});
  useEffect(() => { setF({ name: initial?.name || "", email: initial?.email || "", role: initial?.role || "user", password: "" }); }, [initial, open]);
  const save = async (e) => {
    e.preventDefault();
    try {
      if (isNew) await api.post("/admin/users", f);
      else {
        const body = { name: f.name, email: f.email, password: f.password || undefined };
        if (!initial.is_self) body.role = f.role;
        await api.patch(`/admin/users/${initial.id}`, body);
      }
      toast.success(isNew ? "Account created" : "Account updated");
      onSaved();
    } catch (ex) { toast.error(formatErr(ex)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="user-form-dialog">
        <DialogHeader><DialogTitle className="font-display text-2xl">{isNew ? "New account" : `Edit ${initial?.name}`}</DialogTitle></DialogHeader>
        <form onSubmit={save} className="space-y-3">
          <input className={input} placeholder="Name" value={f.name || ""} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="user-form-name" required />
          <input className={input} type="email" placeholder="Email" value={f.email || ""} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="user-form-email" required />
          <input className={input} type="password" placeholder={isNew ? "Password" : "New password (leave blank to keep)"} value={f.password || ""} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="user-form-password" required={isNew} />
          <select className={input} value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })} disabled={initial?.is_self} data-testid="user-form-role">
            <option value="user">User</option><option value="admin">Admin</option>
          </select>
          <DialogFooter><Btn type="submit" data-testid="user-form-save">{isNew ? "Create account" : "Save changes"}</Btn></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const [users, setUsers] = useState(null);
  const [edit, setEdit] = useState(null);
  const [del, setDel] = useState(null);
  const load = useCallback(() => api.get("/admin/users").then((r) => setUsers(r.data)).catch((e) => toast.error(formatErr(e))), []);
  useEffect(() => { if (user?.role === "admin") load(); }, [user, load]);
  if (user?.role !== "admin") return <Navigate to="/" replace />;
  if (!users) return <Spinner />;
  const remove = async () => {
    try { await api.delete(`/admin/users/${del.id}`); toast.success(`Deleted ${del.name}`); setDel(null); load(); } catch (e) { toast.error(formatErr(e)); }
  };
  return (
    <div data-testid="admin-page">
      <PageTitle title="Manage accounts" sub="Create, edit, reset passwords and remove family accounts.">
        <Btn onClick={() => setEdit({})} data-testid="admin-create-user-button"><UserPlus className="h-5 w-5" /> New account</Btn>
      </PageTitle>
      <div className="overflow-x-auto rounded-3xl border border-slate-200/60 bg-white">
        <table className="w-full text-left text-sm" data-testid="admin-users-table">
          <thead className="bg-slate-50 text-xs uppercase tracking-[0.15em] text-slate-500">
            <tr><th className="p-4">Name</th><th className="p-4">Email</th><th className="p-4">Role</th><th className="p-4">Cards</th><th className="p-4">Value</th><th className="p-4">Joined</th><th className="p-4" /></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-t border-slate-100" data-testid={`admin-user-row-${u.id}`}>
                <td className="p-4 font-display font-bold">{u.name}{u.is_self && <span className="ml-2 text-xs text-slate-400">(you)</span>}</td>
                <td className="p-4">{u.email}</td>
                <td className="p-4">{u.role === "admin" ? <span className="inline-flex items-center gap-1 rounded-full bg-[#FFCC00] px-2 py-0.5 text-xs font-bold"><Shield className="h-3 w-3" /> Admin</span> : <span className="text-slate-500">User</span>}</td>
                <td className="p-4">{u.total_cards}</td>
                <td className="p-4 font-bold">{gbp(u.value_gbp)}</td>
                <td className="p-4 text-slate-500">{u.created_at?.slice(0, 10)}</td>
                <td className="p-4">
                  <div className="flex justify-end gap-1">
                    <button onClick={() => setEdit(u)} className="rounded-full p-2 hover:bg-slate-100" data-testid={`admin-edit-${u.id}`}><Pencil className="h-4 w-4" /></button>
                    {!u.is_self && <button onClick={() => setDel(u)} className="rounded-full p-2 text-red-500 hover:bg-red-50" data-testid={`admin-delete-${u.id}`}><Trash2 className="h-4 w-4" /></button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-4 text-sm text-slate-500">Note: the main admin's password is set by ADMIN_PASSWORD in your .env and is restored on restart.</p>
      <UserForm open={!!edit} initial={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />
      <AlertDialog open={!!del} onOpenChange={(o) => !o && setDel(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {del?.name}?</AlertDialogTitle>
            <AlertDialogDescription>This permanently removes the account and its collection, goals, wishlist and history.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="admin-delete-cancel">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={remove} className="bg-red-600 hover:bg-red-700" data-testid="admin-delete-confirm">Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
