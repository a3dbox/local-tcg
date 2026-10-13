import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Search, Target } from "lucide-react";
import { api, logoImg } from "@/lib/api";
import { PageTitle, Spinner, Chips } from "@/components/UI";

const SetTile = ({ s, owned, tracked }) => {
  const total = s.cardCount?.total || 0;
  const pct = total ? Math.min(100, Math.round((owned / total) * 100)) : 0;
  return (
    <Link to={`/sets/${s.id}`} data-testid={`set-tile-${s.id}`} className="group relative flex flex-col rounded-3xl border border-slate-200/60 bg-white p-4 shadow-[0_4px_12px_rgba(0,0,0,0.05)] transition-[transform,box-shadow] duration-300 hover:-translate-y-1 hover:shadow-[0_12px_24px_rgba(0,0,0,0.1)]">
      {tracked && <Target className="absolute right-3 top-3 h-5 w-5 text-[#E3350D]" strokeWidth={2.5} />}
      <div className="flex h-20 items-center justify-center">
        {s.logo ? <img src={logoImg(s.logo)} alt={s.name} loading="lazy" className="max-h-20 max-w-full object-contain transition-transform group-hover:scale-105" /> : <p className="text-center font-display text-lg font-black">{s.name}</p>}
      </div>
      <p className="mt-3 truncate font-display font-bold">{s.name}</p>
      <div className="mt-1 flex items-center justify-between text-xs text-slate-500">
        <span className="font-mono">{s.id}</span><span className="font-bold">{owned}/{total}</span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-gradient-to-r from-[#FFCC00] to-[#E3350D]" style={{ width: `${pct}%` }} /></div>
    </Link>
  );
};

export default function Sets() {
  const [d, setD] = useState(null);
  const [q, setQ] = useState("");
  const [serie, setSerie] = useState("");
  const [mine, setMine] = useState("");
  useEffect(() => { api.get("/sets").then((r) => setD(r.data)); }, []);
  const groups = useMemo(() => {
    if (!d) return [];
    return d.series.filter((g) => !serie || g.id === serie).map((g) => ({
      ...g,
      sets: g.sets.filter((s) => (!q || s.name.toLowerCase().includes(q.toLowerCase())) && (!mine || (mine === "started" ? d.owned_counts[s.id] : d.goals.includes(s.id)))),
    })).filter((g) => g.sets.length);
  }, [d, q, serie, mine]);
  if (!d) return <Spinner text="Loading sets…" />;

  return (
    <div data-testid="sets-page">
      <PageTitle title="Sets" sub="Every expansion from Base Set to the newest release. Tap one to see what you're missing." />
      <div className="mb-8 space-y-3">
        <div className="relative max-w-xl">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find a set…" data-testid="sets-search-input"
            className="h-12 w-full rounded-full border border-slate-200 bg-white pl-12 pr-4 outline-none focus:border-[#E3350D]" />
        </div>
        <Chips testid="sets-filter-mine" options={[{ value: "started", label: "Sets I've started" }, { value: "tracked", label: "Tracked goals" }]} value={mine} onChange={setMine} />
        <Chips testid="sets-filter-series" options={d.series.map((g) => ({ value: g.id, label: g.name }))} value={serie} onChange={setSerie} />
      </div>
      <div className="space-y-12">
        {groups.map((g) => (
          <section key={g.id} data-testid={`series-${g.id}`}>
            <div className="mb-4 flex items-baseline gap-3">
              <h2 className="font-display text-2xl font-black">{g.name}</h2>
              <span className="text-sm text-slate-500">{g.releaseDate?.slice(0, 4)} · {g.sets.length} sets</span>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
              {g.sets.map((s) => <SetTile key={s.id} s={s} owned={d.owned_counts[s.id] || 0} tracked={d.goals.includes(s.id)} />)}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
