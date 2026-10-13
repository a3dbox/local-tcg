import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search as SearchIcon, X } from "lucide-react";
import { toast } from "sonner";
import { api, formatErr, TYPE_COLORS } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { Chips, PageTitle, Spinner, Empty, Btn } from "@/components/UI";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const CATS = ["Pokemon", "Trainer", "Energy"];
const SORTS = [{ v: "none", l: "Default order" }, { v: "name", l: "Name A–Z" }, { v: "-name", l: "Name Z–A" }, { v: "localId", l: "Card number" }, { v: "-hp", l: "Highest HP" }];

const FilterSelect = ({ value, onChange, placeholder, options, testid }) => (
  <Select value={value || "all"} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
    <SelectTrigger className="h-11 w-full rounded-full border-slate-200 bg-white font-semibold sm:w-56" data-testid={testid}><SelectValue placeholder={placeholder} /></SelectTrigger>
    <SelectContent className="max-h-80">
      <SelectItem value="all">{placeholder}</SelectItem>
      {options.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
    </SelectContent>
  </Select>
);

export default function Search() {
  const [sp, setSp] = useSearchParams();
  const f = Object.fromEntries(["q", "set_id", "type", "rarity", "category", "sort"].map((k) => [k, sp.get(k) || ""]));
  const [text, setText] = useState(f.q);
  const [meta, setMeta] = useState({ types: [], rarities: [], sets: [] });
  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const key = sp.toString();

  const setF = (k, v) => { const n = new URLSearchParams(sp); v ? n.set(k, v) : n.delete(k); setSp(n, { replace: true }); };
  useEffect(() => { api.get("/meta").then((r) => setMeta(r.data)); }, []);
  useEffect(() => { const t = setTimeout(() => text !== f.q && setF("q", text), 400); return () => clearTimeout(t); }); // eslint-disable-line

  const load = async (p) => {
    setLoading(true);
    try {
      const params = { ...Object.fromEntries(Object.entries(f).filter(([, v]) => v && v !== "none")), page: p, size: 36 };
      const { data } = await api.get("/cards", { params });
      setItems((prev) => (p === 1 ? data.items : [...prev, ...data.items]));
      setMore(data.has_more);
      setPage(p);
    } catch (e) { toast.error(formatErr(e)); } finally { setLoading(false); }
  };
  useEffect(() => { load(1); }, [key]); // eslint-disable-line
  const hasFilters = Object.values(f).some(Boolean);

  return (
    <div data-testid="search-page">
      <PageTitle title="Card search" sub="Every Pokémon TCG card ever printed — past, present and newly released." />
      <div className="space-y-4 rounded-3xl border border-slate-200/60 bg-white/80 p-4 backdrop-blur sm:p-6">
        <div className="relative">
          <SearchIcon className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Search by name… e.g. Charizard, Pikachu ex, Professor"
            className="h-14 w-full rounded-full border border-slate-200 bg-slate-50 pl-12 pr-4 text-lg outline-none focus:border-[#E3350D] focus:ring-2 focus:ring-[#E3350D]/20" data-testid="search-input" />
        </div>
        <Chips testid="filter-category" options={CATS} value={f.category} onChange={(v) => setF("category", v)} />
        <Chips testid="filter-type" options={meta.types} value={f.type} onChange={(v) => setF("type", v)} colors={TYPE_COLORS} />
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <FilterSelect testid="filter-set" value={f.set_id} onChange={(v) => setF("set_id", v)} placeholder="All sets" options={meta.sets.map((s) => ({ value: s.id, label: s.name }))} />
          <FilterSelect testid="filter-rarity" value={f.rarity} onChange={(v) => setF("rarity", v)} placeholder="All rarities" options={meta.rarities.map((r) => ({ value: r, label: r }))} />
          <FilterSelect testid="filter-sort" value={f.sort} onChange={(v) => setF("sort", v)} placeholder="Default order" options={SORTS.slice(1).map((s) => ({ value: s.v, label: s.l }))} />
          {hasFilters && <Btn variant="ghost" onClick={() => { setText(""); setSp({}); }} data-testid="clear-filters-button"><X className="h-4 w-4" /> Clear</Btn>}
        </div>
      </div>
      <div className="mt-8">
        {loading && page === 1 ? <Spinner text="Searching cards…" /> : items.length === 0 ? (
          <Empty testid="search-empty" title="No cards found" text="Try a different name or remove some filters." />
        ) : (
          <CardGrid testid="search-results-grid">
            {items.map((c, i) => <CardTile key={c.id} card={c} owned={c.owned} index={i % 36} />)}
          </CardGrid>
        )}
        {more && !loading && <div className="mt-8 flex justify-center"><Btn variant="dark" onClick={() => load(page + 1)} data-testid="load-more-button">Load more cards</Btn></div>}
        {loading && page > 1 && <Spinner />}
      </div>
    </div>
  );
}
