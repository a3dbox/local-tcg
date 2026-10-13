import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import confetti from "canvas-confetti";
import { Target, X, LayoutGrid, BookOpen } from "lucide-react";
import { Binder } from "@/components/Binder";
import { api, formatErr, logoImg, gbp } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { ProgressBar, Spinner, Chips, Btn } from "@/components/UI";

const TARGETS = [{ value: "base", label: "Base set" }, { value: "full", label: "Full set (incl. secrets)" }, { value: "master", label: "Master set (all variants)" }];

export default function SetDetail() {
  const { id } = useParams();
  const [sp, setSp] = useSearchParams();
  const view = sp.get("view") || "";
  const [layout, setLayoutState] = useState(() => localStorage.getItem("pb_set_layout") || "grid");
  const setLayout = (v) => { localStorage.setItem("pb_set_layout", v); setLayoutState(v); };
  const [d, setD] = useState(null);
  const [det, setDet] = useState(null);
  const load = useCallback(() => api.get(`/sets/${id}`).then((r) => setD(r.data)), [id]);
  useEffect(() => { setD(null); setDet(null); load(); api.get(`/sets/${id}/details`).then((r) => setDet(r.data)).catch(() => setDet({})); }, [id, load]);

  const cards = useMemo(() => {
    if (!d) return [];
    return d.set.cards.filter((c) => {
      const has = !!d.owned[c.id];
      return view === "owned" ? has : view === "missing" ? !has : true;
    });
  }, [d, view]);
  const missingValue = useMemo(() => {
    if (!d || !det) return null;
    return d.set.cards.filter((c) => !d.owned[c.id]).reduce((a, c) => a + (det[c.id]?.price_gbp || 0), 0);
  }, [d, det]);

  if (!d) return <Spinner text="Opening set…" />;
  const s = d.set;
  const p = d.progress;

  const setGoal = async (target) => {
    if (target) await api.post("/goals", { set_id: id, target }); else await api.delete(`/goals/${id}`);
    toast.success(target ? "Set goal saved" : "Stopped tracking set");
    load();
  };
  const quickAdd = async (c) => {
    const variant = det?.[c.id]?.variants?.[0] || "normal";
    try {
      await api.post("/collection/add", { card_id: c.id, variant });
      toast.success(`Added ${c.name}`);
      const before = p[d.goal || "base"];
      const r = await api.get(`/sets/${id}`);
      setD(r.data);
      const after = r.data.progress[d.goal || "base"];
      if (after[0] >= after[1] && before[0] < before[1]) confetti({ particleCount: 200, spread: 100 });
    } catch (e) { toast.error(formatErr(e)); }
  };

  return (
    <div data-testid="set-detail-page">
      <div className="rise mb-8 grid gap-6 rounded-[28px] border border-slate-200/60 bg-white p-6 shadow-[0_8px_30px_rgba(0,0,0,0.06)] md:grid-cols-[240px_1fr] md:p-8">
        <div className="flex items-center justify-center">{s.logo ? <img src={logoImg(s.logo)} alt={s.name} className="max-h-32 object-contain" /> : null}</div>
        <div className="space-y-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">{s.serie?.name} · {s.releaseDate}</p>
            <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl" data-testid="set-name">{s.name}</h1>
            <p className="mt-1 text-slate-600">{s.cardCount?.official} official cards · {s.cardCount?.total} total{s.abbreviation?.official ? ` · ${s.abbreviation.official}` : ""}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            <ProgressBar testid="progress-base" label="Base" value={p.base[0]} total={p.base[1]} />
            <ProgressBar testid="progress-full" label="Full" value={p.full[0]} total={p.full[1]} />
            <ProgressBar testid="progress-master" label="Master" value={p.master[0]} total={p.master[1]} />
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Target className="h-5 w-5 text-[#E3350D]" />
            <span className="mr-1 font-display font-bold">{d.goal ? "Tracking:" : "Track this set:"}</span>
            {TARGETS.map((t) => (
              <button key={t.value} onClick={() => setGoal(t.value)} data-testid={`goal-${t.value}-button`}
                className={`press rounded-full px-4 py-1.5 text-sm font-bold ${d.goal === t.value ? "bg-[#E3350D] text-white" : "border border-slate-200 bg-white"}`}>{t.label}</button>
            ))}
            {d.goal && <button onClick={() => setGoal(null)} className="press flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-bold text-slate-500" data-testid="goal-remove-button"><X className="h-4 w-4" /> Stop</button>}
          </div>
          {missingValue != null && <p className="text-sm text-slate-600" data-testid="missing-value">Cost to complete (market): <span className="font-display text-lg font-black text-slate-900">{gbp(missingValue)}</span></p>}
        </div>
      </div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex rounded-full bg-white p-1 shadow-sm" data-testid="set-layout-toggle">
            {[["grid", "Grid", LayoutGrid], ["binder", "Binder", BookOpen]].map(([v, l, Icon]) => (
              <button key={v} onClick={() => setLayout(v)} data-testid={`set-layout-${v}`}
                className={`press flex items-center gap-1.5 rounded-full px-4 py-1.5 font-display text-sm font-bold ${layout === v ? "bg-slate-900 text-white" : "text-slate-600"}`}><Icon className="h-4 w-4" /> {l}</button>
            ))}
          </div>
          {layout === "grid" && <Chips testid="set-view-filter" value={view} onChange={(v) => { const n = new URLSearchParams(sp); v ? n.set("view", v) : n.delete("view"); setSp(n, { replace: true }); }}
            options={[{ value: "owned", label: `Owned (${Object.keys(d.owned).length})` }, { value: "missing", label: `Missing (${s.cards.length - Object.keys(d.owned).length})` }]} />}
        </div>
        <Btn variant="ghost" className="text-sm" onClick={() => window.print()} data-testid="print-checklist-button">Print checklist</Btn>
      </div>
      {layout === "binder" ? <Binder cards={s.cards} owned={d.owned} details={det} /> : (
      <CardGrid testid="set-cards-grid">
        {cards.map((c, i) => {
          const owned = Object.values(d.owned[c.id] || {}).reduce((a, b) => a + b, 0);
          return <CardTile key={c.id} card={c} index={i} owned={owned} missing={!owned} price={det?.[c.id]?.price_gbp} onQuickAdd={quickAdd} />;
        })}
      </CardGrid>
      )}
    </div>
  );
}
