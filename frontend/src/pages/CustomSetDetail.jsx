import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Pencil, Trash2, LayoutGrid, BookOpen, X } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { Binder } from "@/components/Binder";
import { ProgressBar, Spinner, Chips, Btn, Empty } from "@/components/UI";
import { CustomSetDialog, describeRules } from "@/pages/CustomSets";

export default function CustomSetDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [view, setView] = useState("");
  const [layout, setLayout] = useState("grid");
  const [edit, setEdit] = useState(false);
  const load = useCallback(() => api.get(`/custom-sets/${id}`).then((r) => setD(r.data)).catch((e) => toast.error(formatErr(e))), [id]);
  useEffect(() => { load(); }, [load]);
  const cards = useMemo(() => (d ? d.cards.filter((c) => (view === "owned" ? d.owned[c.id] : view === "missing" ? !d.owned[c.id] : true)) : []), [d, view]);
  if (!d) return <Spinner text="Gathering cards…" />;

  const quickAdd = async (c) => {
    try { await api.post("/collection/add", { card_id: c.id }); toast.success(`Added ${c.name}`); load(); } catch (e) { toast.error(formatErr(e)); }
  };
  const removeCard = async (c) => { await api.delete(`/custom-sets/${id}/cards/${c.id}`); toast(`Removed ${c.name} from this set`); load(); };
  const del = async () => { if (!window.confirm(`Delete “${d.name}”? Your owned cards are not affected.`)) return; await api.delete(`/custom-sets/${id}`); nav("/my-sets"); };
  const ownedCount = d.cards.filter((c) => d.owned[c.id]).length;

  return (
    <div data-testid="custom-set-detail-page">
      <div className="rise mb-8 rounded-[28px] border border-slate-200/60 bg-white p-6 shadow-[0_8px_30px_rgba(0,0,0,0.06)] md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Custom set</p>
            <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl" data-testid="custom-set-name">{d.name}</h1>
            <p className="mt-1 text-slate-600" data-testid="custom-set-rules">{describeRules(d.rules)}{d.card_ids.length ? ` · ${d.card_ids.length} hand-picked` : ""}</p>
          </div>
          <div className="flex gap-2">
            <Btn variant="ghost" onClick={() => setEdit(true)} data-testid="custom-set-edit-button"><Pencil className="h-4 w-4" /> Edit</Btn>
            <Btn variant="ghost" onClick={del} data-testid="custom-set-delete-button"><Trash2 className="h-4 w-4" /> Delete</Btn>
          </div>
        </div>
        <div className="mt-5"><ProgressBar testid="custom-set-progress" size="h-6" label="Collected" value={d.progress[0]} total={d.progress[1]} /></div>
      </div>
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="flex rounded-full bg-white p-1 shadow-sm">
          {[["grid", "Grid", LayoutGrid], ["binder", "Binder", BookOpen]].map(([v, l, Icon]) => (
            <button key={v} onClick={() => setLayout(v)} data-testid={`custom-layout-${v}`} className={`press flex items-center gap-1.5 rounded-full px-4 py-1.5 font-display text-sm font-bold ${layout === v ? "bg-slate-900 text-white" : "text-slate-600"}`}><Icon className="h-4 w-4" /> {l}</button>
          ))}
        </div>
        {layout === "grid" && <Chips testid="custom-set-view" value={view} onChange={setView} options={[{ value: "owned", label: `Owned (${ownedCount})` }, { value: "missing", label: `Missing (${d.cards.length - ownedCount})` }]} />}
      </div>
      {d.cards.length === 0 ? <Empty testid="custom-set-empty" title="No cards yet" text="Edit the rules, or open any card and use “Add to my set”." /> : layout === "binder" ? <Binder cards={d.cards} owned={d.owned} /> : (
        <CardGrid testid="custom-set-grid">
          {cards.map((c, i) => {
            const owned = Object.values(d.owned[c.id] || {}).reduce((a, b) => a + b, 0);
            return (
              <div key={c.id} className="relative">
                <CardTile card={c} index={i} owned={owned} missing={!owned} onQuickAdd={quickAdd} />
                <button onClick={() => removeCard(c)} aria-label="Remove from set" data-testid={`custom-remove-${c.id}`} className="absolute left-3 top-3 rounded-full bg-white/90 p-1 text-slate-500 shadow hover:text-red-600"><X className="h-4 w-4" /></button>
              </div>
            );
          })}
        </CardGrid>
      )}
      <CustomSetDialog open={edit} initial={d} onClose={() => setEdit(false)} onSaved={() => { setEdit(false); load(); }} />
    </div>
  );
}
