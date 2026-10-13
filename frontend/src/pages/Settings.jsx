import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Database, Play } from "lucide-react";
import { api, formatErr } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { PageTitle, Btn, ProgressBar } from "@/components/UI";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export default function Settings() {
  const { user, logout } = useAuth();
  const [st, setSt] = useState(null);
  const [sets, setSets] = useState([]);
  const [pick, setPick] = useState("");
  useEffect(() => {
    const tick = () => api.get("/scan/index/status").then((r) => setSt(r.data));
    tick();
    const t = setInterval(tick, 2500);
    api.get("/meta").then((r) => setSets(r.data.sets));
    return () => clearInterval(t);
  }, []);
  const start = async (body) => {
    try { await api.post("/scan/index", body); toast.success("Indexing started"); } catch (e) { toast.error(formatErr(e)); }
  };
  return (
    <div className="max-w-3xl space-y-6" data-testid="settings-page">
      <PageTitle title="Settings" />
      <div className="rounded-3xl border border-slate-200/60 bg-white p-6">
        <h2 className="font-display text-xl font-bold">Account</h2>
        <p className="mt-2 text-slate-600"><b>{user?.name}</b> · {user?.email} · {user?.role}</p>
        <p className="mt-1 text-sm text-slate-500">Each account has its own private collection, goals and wishlist. Create another account for each family member.</p>
        <Btn variant="ghost" className="mt-4" onClick={logout} data-testid="settings-logout-button">Log out</Btn>
      </div>
      <div className="rounded-3xl border border-slate-200/60 bg-white p-6">
        <h2 className="flex items-center gap-2 font-display text-xl font-bold"><Database className="h-5 w-5 text-[#E3350D]" /> Scanner card database</h2>
        <p className="mt-2 text-sm text-slate-600">
          The scanner recognises cards on your own server by reading the card number &amp; name (OCR) and comparing the picture against visual fingerprints of real card images.
          Fingerprints are learned automatically as you scan; pre-indexing sets makes recognition faster and more accurate — especially for cards whose number is hard to read.
        </p>
        {st && (
          <div className="mt-5 space-y-3 rounded-2xl bg-slate-50 p-4" data-testid="index-status">
            <p className="font-display font-bold">{st.indexed.toLocaleString()} cards fingerprinted</p>
            {st.running && <ProgressBar label={`Indexing ${st.current || ""}`} value={st.done} total={st.total} />}
          </div>
        )}
        <div className="mt-5 flex flex-wrap gap-3">
          <Btn onClick={() => start({ goals_only: true })} disabled={st?.running} data-testid="index-goals-button"><Play className="h-4 w-4" /> Index my tracked sets</Btn>
          <Btn variant="dark" onClick={() => start({})} disabled={st?.running} data-testid="index-all-button">Index ALL sets (~20k cards)</Btn>
        </div>
        <div className="mt-4 flex flex-col gap-3 sm:flex-row">
          <Select value={pick} onValueChange={setPick}>
            <SelectTrigger className="h-11 rounded-full sm:w-72" data-testid="index-set-select"><SelectValue placeholder="Pick a single set…" /></SelectTrigger>
            <SelectContent className="max-h-80">{sets.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}</SelectContent>
          </Select>
          <Btn variant="ghost" disabled={!pick || st?.running} onClick={() => start({ set_ids: [pick] })} data-testid="index-set-button">Index this set</Btn>
        </div>
      </div>
    </div>
  );
}
