import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api, artwork } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { PageTitle, Spinner, Chips, Empty } from "@/components/UI";

const GENS = [[1, 151], [152, 251], [252, 386], [387, 493], [494, 649], [650, 721], [722, 809], [810, 905], [906, 1025]];
const cap = (s) => s.split("-").map((w) => w[0].toUpperCase() + w.slice(1)).join(" ");

export function Pokedex() {
  const [list, setList] = useState(null);
  const [q, setQ] = useState("");
  const [gen, setGen] = useState("1");
  useEffect(() => { api.get("/pokedex").then((r) => setList(r.data)); }, []);
  const shown = useMemo(() => {
    if (!list) return [];
    if (q) return list.filter((p) => p.name.includes(q.toLowerCase()) || String(p.id) === q);
    const [a, b] = GENS[Number(gen || 1) - 1] || [1, 99999];
    return list.filter((p) => p.id >= a && (gen === "10" ? p.id > 1025 : p.id <= b));
  }, [list, q, gen]);
  if (!list) return <Spinner text="Loading Pokédex…" />;
  const opts = GENS.map((_, i) => ({ value: String(i + 1), label: `Gen ${i + 1}` }));
  if (list.some((p) => p.id > 1025)) opts.push({ value: "10", label: "New" });
  return (
    <div data-testid="pokedex-page">
      <PageTitle title="Pokédex" sub={`All ${list.length} Pokémon. Tap one to see every card ever made of it.`} />
      <div className="mb-6 space-y-3">
        <div className="relative max-w-xl">
          <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Name or number…" data-testid="pokedex-search-input" className="h-12 w-full rounded-full border border-slate-200 bg-white pl-12 pr-4 outline-none focus:border-[#E3350D]" />
        </div>
        {!q && <Chips testid="pokedex-gen-filter" options={opts} value={gen} onChange={(v) => setGen(v || "1")} />}
      </div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
        {shown.map((p) => (
          <Link key={p.id} to={`/pokedex/${p.id}`} data-testid={`pokedex-entry-${p.id}`} className="group rounded-2xl border border-slate-200/60 bg-white p-2 text-center transition-transform hover:-translate-y-1">
            <img src={artwork(p.id)} alt={p.name} loading="lazy" className="mx-auto aspect-square w-full object-contain transition-transform group-hover:scale-110" />
            <p className="font-mono text-[10px] text-slate-400">#{String(p.id).padStart(4, "0")}</p>
            <p className="truncate font-display text-sm font-bold">{cap(p.name)}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function PokemonCards() {
  const { dex } = useParams();
  const [cards, setCards] = useState(null);
  const [name, setName] = useState("");
  useEffect(() => {
    setCards(null);
    api.get("/cards", { params: { dex, size: 250 } }).then((r) => setCards(r.data.items));
    api.get("/pokedex").then((r) => setName(cap(r.data.find((p) => String(p.id) === dex)?.name || "")));
  }, [dex]);
  const owned = cards?.filter((c) => c.owned).length || 0;
  return (
    <div data-testid="pokemon-cards-page">
      <div className="mb-8 flex items-center gap-6">
        <img src={artwork(dex)} alt={name} className="h-28 w-28 object-contain sm:h-36 sm:w-36" />
        <div>
          <p className="font-mono text-sm text-slate-500">#{String(dex).padStart(4, "0")}</p>
          <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">{name}</h1>
          {cards && <p className="mt-1 text-slate-600" data-testid="pokemon-owned-summary">You own {owned} of {cards.length} {name} cards</p>}
        </div>
      </div>
      {!cards ? <Spinner /> : cards.length === 0 ? <Empty title="No cards yet" text="This Pokémon hasn't appeared in the TCG yet." /> : (
        <CardGrid testid="pokemon-cards-grid">{cards.map((c, i) => <CardTile key={c.id} card={c} owned={c.owned} missing={!c.owned} index={i % 30} />)}</CardGrid>
      )}
    </div>
  );
}
