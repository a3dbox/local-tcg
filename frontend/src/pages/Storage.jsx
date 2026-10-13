import { useEffect, useState, useCallback } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { Plus, Pencil, Trash2, Archive, BookOpen, Box, Layers3, Package, Briefcase, Inbox } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr, gbp, cardImg, vLabel } from "@/lib/api";
import { PageTitle, Spinner, Empty, Btn } from "@/components/UI";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

export const KINDS = { binder: ["Binder", BookOpen], case: ["Case", Briefcase], box: ["Box", Box], deck: ["Deck box", Layers3], bulk: ["Bulk", Package], other: ["Other", Archive] };
const input = "w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-[#E3350D]";

function LocationDialog({ open, initial, onClose, onSaved }) {
  const [f, setF] = useState({});
  useEffect(() => { if (open) setF({ name: initial?.name || "", kind: initial?.kind || "case", description: initial?.description || "" }); }, [open, initial]);
  const save = async () => {
    try {
      if (initial?.id) await api.patch(`/locations/${initial.id}`, f); else await api.post("/locations", f);
      toast.success("Saved");
      onSaved();
    } catch (e) { toast.error(formatErr(e)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="location-dialog">
        <DialogHeader><DialogTitle className="font-display text-2xl">{initial?.id ? "Edit storage" : "New storage"}</DialogTitle></DialogHeader>
        <input className={input} placeholder="Name, e.g. Red card case, Bulk box 1" value={f.name || ""} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="location-name-input" />
        <div className="flex flex-wrap gap-2" data-testid="location-kind-chips">
          {Object.entries(KINDS).map(([k, [l, Icon]]) => (
            <button key={k} onClick={() => setF({ ...f, kind: k })} data-testid={`location-kind-${k}`} className={`press flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-bold ${f.kind === k ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200"}`}><Icon className="h-4 w-4" /> {l}</button>
          ))}
        </div>
        <input className={input} placeholder="Notes (optional) — e.g. shelf in bedroom" value={f.description || ""} onChange={(e) => setF({ ...f, description: e.target.value })} data-testid="location-description-input" />
        <DialogFooter><Btn onClick={save} data-testid="location-save-button">Save</Btn></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Storage() {
  const [d, setD] = useState(null);
  const [edit, setEdit] = useState(null);
  const load = useCallback(() => api.get("/locations").then((r) => setD(r.data)), []);
  useEffect(() => { load(); }, [load]);
  if (!d) return <Spinner />;
  return (
    <div data-testid="storage-page">
      <PageTitle title="Storage" sub="Cases, binders, boxes and bulk — know exactly where every card lives.">
        <Btn onClick={() => setEdit({})} data-testid="new-location-button"><Plus className="h-5 w-5" /> New storage</Btn>
      </PageTitle>
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        <Link to="/storage/unassigned" className="rounded-3xl border-2 border-dashed border-slate-300 bg-white/70 p-6 transition-transform hover:-translate-y-1" data-testid="location-card-unassigned">
          <Inbox className="h-8 w-8 text-slate-400" />
          <p className="mt-3 font-display text-xl font-black">Not stored yet</p>
          <p className="text-sm text-slate-500">{d.unassigned.cards} cards · {d.unassigned.unique} unique · {gbp(d.unassigned.value_gbp)}</p>
        </Link>
        {d.locations.map((l) => {
          const [label, Icon] = KINDS[l.kind] || KINDS.other;
          return (
            <Link key={l.id} to={`/storage/${l.id}`} className="rise rounded-3xl border border-slate-200/60 bg-white p-6 shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-transform hover:-translate-y-1" data-testid={`location-card-${l.id}`}>
              <div className="flex items-center justify-between"><Icon className="h-8 w-8 text-[#E3350D]" /><span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-bold">{label}</span></div>
              <p className="mt-3 truncate font-display text-xl font-black">{l.name}</p>
              {l.description && <p className="truncate text-sm text-slate-500">{l.description}</p>}
              <p className="mt-2 text-sm font-semibold text-slate-600">{l.cards} cards · {l.unique} unique · {gbp(l.value_gbp)}</p>
            </Link>
          );
        })}
      </div>
      <LocationDialog open={!!edit} initial={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />
    </div>
  );
}

export function MoveSelect({ item, from, locations, onMoved, testid }) {
  const move = async (to) => {
    if (!to) return;
    try {
      await api.post("/locations/move", { item_id: item.item_id || item.id, from_id: from, to_id: to, quantity: 1 });
      toast.success(`Moved 1 × ${item.name || "card"}`);
      onMoved();
    } catch (e) { toast.error(formatErr(e)); }
  };
  return (
    <select value="" onChange={(e) => move(e.target.value)} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold" data-testid={testid}>
      <option value="">Move 1 to…</option>
      {from !== "unassigned" && <option value="unassigned">Not stored</option>}
      {locations.filter((l) => l.id !== from).map((l) => <option key={l.id} value={l.id}>{String(l.name)}</option>)}
    </select>
  );
}

export function StorageDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [locs, setLocs] = useState([]);
  const [edit, setEdit] = useState(false);
  const isUn = id === "unassigned";
  const load = useCallback(async () => {
    const all = (await api.get("/locations")).data;
    setLocs(all.locations);
    if (isUn) { const items = (await api.get("/locations/unassigned/items")).data; setD({ location: { name: "Not stored yet", kind: "other" }, items, cards: items.reduce((a, i) => a + i.placed, 0), value_gbp: all.unassigned.value_gbp }); }
    else setD((await api.get(`/locations/${id}`)).data);
  }, [id, isUn]);
  useEffect(() => { load().catch((e) => toast.error(formatErr(e))); }, [load]);
  if (!d) return <Spinner />;
  const del = async () => { if (!window.confirm(`Delete “${d.location.name}”? Cards inside become “not stored”.`)) return; await api.delete(`/locations/${id}`); nav("/storage"); };
  const [label, Icon] = KINDS[d.location.kind] || KINDS.other;
  return (
    <div data-testid="storage-detail-page">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div className="flex items-center gap-4">
          <Icon className="h-12 w-12 text-[#E3350D]" />
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">{isUn ? "Unsorted cards" : label}</p>
            <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl" data-testid="storage-name">{d.location.name}</h1>
            <p className="text-slate-600" data-testid="storage-summary">{d.cards} cards · {gbp(d.value_gbp)}{d.location.description ? ` · ${d.location.description}` : ""}</p>
          </div>
        </div>
        {!isUn && <div className="flex gap-2"><Btn variant="ghost" onClick={() => setEdit(true)} data-testid="storage-edit-button"><Pencil className="h-4 w-4" /> Edit</Btn><Btn variant="ghost" onClick={del} data-testid="storage-delete-button"><Trash2 className="h-4 w-4" /> Delete</Btn></div>}
      </div>
      {d.items.length === 0 ? <Empty testid="storage-empty" title="Nothing here yet" text={isUn ? "Every card has a home!" : "Move cards here from “Not stored yet”, a card page, or choose this storage when batch scanning."} /> : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" data-testid="storage-items">
          {d.items.map((it) => (
            <div key={it.id} className="flex gap-3 rounded-2xl border border-slate-200/60 bg-white p-3" data-testid={`storage-item-${it.id}`}>
              <Link to={`/card/${it.card_id}`}><img src={cardImg(it.image)} alt={it.name} className="h-24 w-[68px] rounded-lg object-cover" /></Link>
              <div className="min-w-0 flex-1">
                <p className="truncate font-display font-bold">{it.name}</p>
                <p className="truncate text-xs text-slate-500">{it.set_name} · #{it.local_id} · {vLabel(it.variant)}</p>
                <p className="mt-1 text-sm"><b>{it.placed}</b> here · {it.quantity} owned · {gbp(it.price_gbp)}</p>
                <div className="mt-2"><MoveSelect item={it} from={id} locations={locs} onMoved={load} testid={`storage-move-${it.id}`} /></div>
              </div>
            </div>
          ))}
        </div>
      )}
      <LocationDialog open={edit} initial={{ ...d.location, id }} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); load(); }} />
    </div>
  );
}
