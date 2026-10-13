import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, RefreshCw, Search } from "lucide-react";
import { toast } from "sonner";
import { api, usd, eur, API_BASE } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { PageTitle, Spinner, Empty, Btn, Chips } from "@/components/UI";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const SORTS = [["recent", "Recently added"], ["value", "Highest value"], ["name", "Name"], ["set", "Set & number"]];

export default function Collection() {
  const [items, setItems] = useState(null);
  const [stats, setStats] = useState(null);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("recent");
  const [variant, setVariant] = useState("");
  useEffect(() => {
    const t = setTimeout(() => api.get("/collection", { params: { q: q || undefined, sort, variant: variant || undefined } }).then((r) => setItems(r.data)), 250);
    return () => clearTimeout(t);
  }, [q, sort, variant]);
  useEffect(() => { api.get("/collection/stats").then((r) => setStats(r.data)); }, []);

  const exportCsv = async () => {
    const r = await api.get("/collection/export", { responseType: "blob" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(r.data);
    a.download = "pokebinder-collection.csv";
    a.click();
  };
  const refresh = async () => { await api.post("/collection/refresh-prices"); toast.success("Refreshing prices in the background…"); };

  return (
    <div data-testid="collection-page">
      <PageTitle title="My cards" sub="Everything in your binder, with live market values.">
        <div className="flex gap-2">
          <Btn variant="ghost" onClick={refresh} data-testid="refresh-prices-button"><RefreshCw className="h-4 w-4" /> Prices</Btn>
          <Btn variant="ghost" onClick={exportCsv} data-testid="export-csv-button" data-api={API_BASE}><Download className="h-4 w-4" /> CSV</Btn>
        </div>
      </PageTitle>
      {stats && (
        <div className="mb-6 flex flex-wrap gap-3" data-testid="collection-stats">
          {[["Value", `${usd(stats.value_usd)} · ${eur(stats.value_eur)}`], ["Cards", stats.total_cards], ["Unique", stats.unique_cards], ["Sets", stats.sets_started]].map(([k, v]) => (
            <div key={k} className="rounded-full bg-white px-5 py-2 shadow-sm"><span className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">{k}</span> <span className="ml-1 font-display font-black">{v}</span></div>
          ))}
        </div>
      )}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search my cards…" data-testid="collection-search-input" className="h-12 w-full rounded-full border border-slate-200 bg-white pl-12 pr-4 outline-none focus:border-[#E3350D]" />
        </div>
        <Select value={sort} onValueChange={setSort}>
          <SelectTrigger className="h-12 rounded-full bg-white font-semibold sm:w-52" data-testid="collection-sort-select"><SelectValue /></SelectTrigger>
          <SelectContent>{SORTS.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}</SelectContent>
        </Select>
      </div>
      <div className="mb-6"><Chips testid="collection-variant-filter" value={variant} onChange={setVariant} options={[{ value: "normal", label: "Normal" }, { value: "holo", label: "Holo" }, { value: "reverse", label: "Reverse Holo" }, { value: "firstEdition", label: "1st Edition" }]} /></div>
      {!items ? <Spinner /> : items.length === 0 ? (
        <Empty testid="collection-empty" title="No cards here yet" text="Scan your cards or add them from any card page.">
          <Link to="/scan"><Btn>Scan cards</Btn></Link><Link to="/search"><Btn variant="ghost">Search</Btn></Link>
        </Empty>
      ) : (
        <CardGrid testid="collection-grid">
          {items.map((it, i) => <CardTile key={it.id} index={i} card={{ id: it.card_id, name: it.name, image: it.image, localId: `${it.local_id} · ${it.set_name || ""}` }} owned={it.quantity} price={it.price_usd} variant={it.variant} />)}
        </CardGrid>
      )}
    </div>
  );
}
