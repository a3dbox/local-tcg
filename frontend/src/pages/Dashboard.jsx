import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ScanLine, Search, Coins, Layers, LibraryBig, Sparkles } from "lucide-react";
import { api, usd, eur, logoImg } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { CardTile, CardGrid } from "@/components/CardTile";
import { ProgressBar, Spinner, Btn } from "@/components/UI";

const Stat = ({ icon: Icon, label, value, sub, testid, accent }) => (
  <div className={`rounded-3xl border border-slate-200/60 p-6 shadow-[0_4px_12px_rgba(0,0,0,0.05)] ${accent || "bg-white"}`} data-testid={testid}>
    <Icon className="h-6 w-6" strokeWidth={2.5} />
    <p className="mt-4 text-xs font-bold uppercase tracking-[0.15em] opacity-70">{label}</p>
    <p className="font-display text-3xl font-black">{value}</p>
    {sub && <p className="text-sm opacity-70">{sub}</p>}
  </div>
);

export default function Dashboard() {
  const { user } = useAuth();
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/dashboard").then((r) => setD(r.data)); }, []);
  if (!d) return <Spinner />;
  const s = d.stats;
  return (
    <div className="space-y-10" data-testid="dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Trainer dashboard</p>
          <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl lg:text-6xl">Hi, {user?.name}!</h1>
        </div>
        <div className="flex gap-3">
          <Link to="/scan"><Btn data-testid="dashboard-scan-button"><ScanLine className="h-5 w-5" /> Scan cards</Btn></Link>
          <Link to="/search"><Btn variant="ghost" data-testid="dashboard-search-button"><Search className="h-5 w-5" /> Search</Btn></Link>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4 sm:gap-6">
        <Stat icon={Coins} label="Collection value" value={usd(s.value_usd)} sub={eur(s.value_eur)} testid="stat-value" accent="bg-[#FFCC00]" />
        <Stat icon={LibraryBig} label="Total cards" value={s.total_cards} testid="stat-total-cards" />
        <Stat icon={Sparkles} label="Unique cards" value={s.unique_cards} testid="stat-unique-cards" />
        <Stat icon={Layers} label="Sets started" value={s.sets_started} testid="stat-sets-started" />
      </div>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-2xl font-bold">Set goals</h2>
          <Link to="/goals" className="text-sm font-bold text-[#E3350D]" data-testid="dashboard-goals-link">All goals →</Link>
        </div>
        {d.goals.length === 0 ? (
          <p className="rounded-2xl bg-white p-6 text-slate-600">No sets tracked yet. Open any set in <Link to="/sets" className="font-bold text-[#E3350D]">Sets</Link> and tap “Track this set”.</p>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {d.goals.map((g) => (
              <Link key={g.set_id} to={`/sets/${g.set_id}`} className="rounded-3xl border border-slate-200/60 bg-white p-5 transition-transform hover:-translate-y-1" data-testid={`dashboard-goal-${g.set_id}`}>
                <div className="mb-4 flex h-12 items-center">{g.logo ? <img src={logoImg(g.logo)} alt={g.name} className="max-h-12 max-w-[160px] object-contain" /> : <p className="font-display font-bold">{g.name}</p>}</div>
                <ProgressBar label={`${g.name} · ${g.target}`} value={g.progress[g.target][0]} total={g.progress[g.target][1]} />
              </Link>
            ))}
          </div>
        )}
      </section>

      {d.top.length > 0 && (
        <section>
          <h2 className="mb-4 font-display text-2xl font-bold">Most valuable</h2>
          <CardGrid testid="dashboard-top-grid">
            {d.top.map((it, i) => <CardTile key={it.id} index={i} card={{ id: it.card_id, name: it.name, image: it.image, localId: it.local_id }} owned={it.quantity} price={it.price_usd} variant={it.variant} />)}
          </CardGrid>
        </section>
      )}
      <section>
        <h2 className="mb-4 font-display text-2xl font-bold">Recently added</h2>
        {d.recent.length === 0 ? (
          <p className="rounded-2xl bg-white p-6 text-slate-600">Your binder is empty. Try scanning a card or searching for your favourite Pokémon!</p>
        ) : (
          <CardGrid testid="dashboard-recent-grid">
            {d.recent.map((it, i) => <CardTile key={it.id} index={i} card={{ id: it.card_id, name: it.name, image: it.image, localId: it.local_id }} owned={it.quantity} variant={it.variant} />)}
          </CardGrid>
        )}
      </section>
    </div>
  );
}
