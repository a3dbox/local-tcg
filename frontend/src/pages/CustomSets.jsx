import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Plus, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr, cardImg, TYPE_COLORS } from "@/lib/api";
import { PageTitle, Spinner, Empty, Btn, ProgressBar, Chips } from "@/components/UI";
import { SetSelect } from "@/components/SetSelect";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";

const input = "w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 outline-none focus:border-[#E3350D]";
const IDEAS = [
  { label: "All Darkness Pokémon", rules: { type: "Darkness", category: "Pokemon" } },
  { label: "Every Squirtle", rules: { dex: 7 } },
  { label: "Every Pikachu", rules: { dex: 25 } },
  { label: "Special illustration rares", rules: { rarity: "Special illustration rare" } },
  { label: "Hand-picked cards", rules: {} },
];

export const describeRules = (r = {}) => [r.q && `name ${r.exact ? "=" : "contains"} “${r.q}”`, r.dex && `Pokédex #${r.dex}`, r.type && `${r.type} type`,
  r.category, r.rarity, r.set_id && `set ${r.set_id}`, r.illustrator && `art by ${r.illustrator}`].filter(Boolean).join(" · ") || "Hand-picked cards";

export function RuleBuilder({ rules, setRules }) {
  const [meta, setMeta] = useState({ types: [], rarities: [], sets: [] });
  useEffect(() => { api.get("/meta").then((r) => setMeta(r.data)); }, []);
  const set = (k, v) => setRules({ ...rules, [k]: v || null });
  return (
    <div className="space-y-3" data-testid="rule-builder">
      <div className="grid gap-3 sm:grid-cols-2">
        <input className={input} placeholder="Card name contains… (e.g. Squirtle)" value={rules.q || ""} onChange={(e) => set("q", e.target.value)} data-testid="rule-name-input" />
        <input className={input} type="number" placeholder="Pokédex number (e.g. 7)" value={rules.dex || ""} onChange={(e) => set("dex", e.target.value ? Number(e.target.value) : null)} data-testid="rule-dex-input" />
      </div>
      <label className="flex items-center gap-2 text-sm font-semibold text-slate-600"><input type="checkbox" checked={!!rules.exact} onChange={(e) => setRules({ ...rules, exact: e.target.checked })} data-testid="rule-exact-checkbox" /> Exact name only</label>
      <Chips testid="rule-type" options={meta.types} value={rules.type || ""} onChange={(v) => set("type", v)} colors={TYPE_COLORS} />
      <Chips testid="rule-category" options={["Pokemon", "Trainer", "Energy"]} value={rules.category || ""} onChange={(v) => set("category", v)} />
      <div className="grid gap-3 sm:grid-cols-2">
        <select className={input} value={rules.rarity || ""} onChange={(e) => set("rarity", e.target.value)} data-testid="rule-rarity-select">
          <option value="">Any rarity</option>{meta.rarities.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <SetSelect sets={meta.sets} value={rules.set_id || ""} onChange={(v) => set("set_id", v)} placeholder="Any set" testid="rule-set-select" className="w-full" />
      </div>
      <input className={input} placeholder="Illustrator (optional)" value={rules.illustrator || ""} onChange={(e) => set("illustrator", e.target.value)} data-testid="rule-illustrator-input" />
    </div>
  );
}

export function CustomSetDialog({ open, onClose, initial, onSaved }) {
  const [name, setName] = useState("");
  const [rules, setRules] = useState({});
  useEffect(() => { if (open) { setName(initial?.name || ""); setRules(initial?.rules || {}); } }, [open, initial]);
  const save = async () => {
    try {
      const { data } = initial?.id ? await api.patch(`/custom-sets/${initial.id}`, { name, rules }) : await api.post("/custom-sets", { name, rules, card_ids: initial?.card_ids || [] });
      toast.success("Custom set saved");
      onSaved(data);
    } catch (e) { toast.error(formatErr(e)); }
  };
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl" data-testid="custom-set-dialog">
        <DialogHeader><DialogTitle className="font-display text-2xl">{initial?.id ? "Edit custom set" : "New custom set"}</DialogTitle></DialogHeader>
        <input className={input} placeholder="Name, e.g. My Squirtle collection" value={name} onChange={(e) => setName(e.target.value)} data-testid="custom-set-name-input" />
        {!initial?.id && (
          <div className="flex flex-wrap gap-2">
            {IDEAS.map((i) => <button key={i.label} onClick={() => { setRules(i.rules); if (!name) setName(i.label); }} className="rounded-full bg-[#FFCC00]/30 px-3 py-1 text-xs font-bold hover:bg-[#FFCC00]" data-testid={`idea-${i.label.toLowerCase().replace(/[^a-z]+/g, "-")}`}><Sparkles className="mr-1 inline h-3 w-3" />{i.label}</button>)}
          </div>
        )}
        <p className="text-sm text-slate-500">Cards matching these rules are included automatically (new releases too). Leave empty for a hand-picked set — add cards from any card page.</p>
        <RuleBuilder rules={rules} setRules={setRules} />
        <DialogFooter><Btn onClick={save} data-testid="custom-set-save-button">Save set</Btn></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function CustomSets() {
  const nav = useNavigate();
  const [sets, setSets] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.get("/custom-sets").then((r) => setSets(r.data)); }, []);
  if (!sets) return <Spinner text="Loading your sets…" />;
  return (
    <div data-testid="custom-sets-page">
      <PageTitle title="My custom sets" sub="Build your own sets to collect — all Darkness Pokémon, every Squirtle, or any cards you pick.">
        <Btn onClick={() => setOpen(true)} data-testid="new-custom-set-button"><Plus className="h-5 w-5" /> New set</Btn>
      </PageTitle>
      {sets.length === 0 ? (
        <Empty testid="custom-sets-empty" title="No custom sets yet" text="Create one from rules, or hand-pick cards with the “Add to my set” button on any card."><Btn onClick={() => setOpen(true)}>Create a set</Btn></Empty>
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {sets.map((s) => (
            <Link key={s.id} to={`/my-sets/${s.id}`} className="rise flex gap-4 rounded-3xl border border-slate-200/60 bg-white p-4 shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-transform hover:-translate-y-1" data-testid={`custom-set-card-${s.id}`}>
              {s.cover ? <img src={cardImg(s.cover)} alt="" className="h-28 w-20 shrink-0 rounded-lg object-cover" /> : <div className="h-28 w-20 shrink-0 rounded-lg bg-slate-100" />}
              <div className="min-w-0 flex-1">
                <p className="truncate font-display text-lg font-black">{s.name}</p>
                <p className="mb-3 line-clamp-2 text-xs text-slate-500">{describeRules(s.rules)}</p>
                <ProgressBar value={s.progress[0]} total={s.progress[1]} label="Collected" size="h-3" />
              </div>
            </Link>
          ))}
        </div>
      )}
      <CustomSetDialog open={open} onClose={() => setOpen(false)} onSaved={(d) => nav(`/my-sets/${d.id}`)} />
    </div>
  );
}
