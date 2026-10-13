import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, logoImg, usd } from "@/lib/api";
import { CardTile, CardGrid } from "@/components/CardTile";
import { PageTitle, ProgressBar, Spinner, Empty, Btn } from "@/components/UI";

export function Goals() {
  const [goals, setGoals] = useState(null);
  useEffect(() => { api.get("/goals").then((r) => setGoals(r.data)); }, []);
  if (!goals) return <Spinner />;
  return (
    <div data-testid="goals-page">
      <PageTitle title="Set goals" sub="Sets you're collecting and exactly what's left to find." />
      {goals.length === 0 ? (
        <Empty testid="goals-empty" title="No goals yet" text="Open a set and choose Base, Full or Master to start tracking it."><Link to="/sets"><Btn>Browse sets</Btn></Link></Empty>
      ) : (
        <div className="grid gap-5 md:grid-cols-2">
          {goals.map((g) => {
            const [have, total] = g.progress[g.target];
            return (
              <div key={g.set_id} className="rise rounded-3xl border border-slate-200/60 bg-white p-6 shadow-[0_4px_12px_rgba(0,0,0,0.05)]" data-testid={`goal-card-${g.set_id}`}>
                <div className="flex items-center gap-4">
                  {g.logo && <img src={logoImg(g.logo)} alt="" className="h-14 w-28 object-contain" />}
                  <div className="min-w-0"><p className="truncate font-display text-xl font-black">{g.name}</p><p className="text-sm text-slate-500">{g.serie} · {g.releaseDate}</p></div>
                </div>
                <div className="mt-5 space-y-3">
                  <ProgressBar size="h-6" label={`${g.target} goal`} value={have} total={total} />
                  {g.target !== "base" && <ProgressBar size="h-2" label="Base" value={g.progress.base[0]} total={g.progress.base[1]} />}
                </div>
                <div className="mt-5 flex items-center justify-between">
                  <p className="font-display font-bold">{have >= total ? "Complete!" : `${total - have} to go`}</p>
                  <div className="flex gap-2">
                    <Link to={`/sets/${g.set_id}?view=missing`}><Btn className="px-4 py-2 text-sm" data-testid={`goal-missing-${g.set_id}`}>See missing</Btn></Link>
                    <Link to={`/sets/${g.set_id}`}><Btn variant="ghost" className="px-4 py-2 text-sm">Open</Btn></Link>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function Wishlist() {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get("/wishlist").then((r) => setItems(r.data)); }, []);
  if (!items) return <Spinner />;
  const total = items.reduce((a, i) => a + (i.price_usd || 0), 0);
  return (
    <div data-testid="wishlist-page">
      <PageTitle title="Wishlist" sub={`Cards you're hunting for · about ${usd(total)} at market price.`} />
      {items.length === 0 ? <Empty testid="wishlist-empty" title="Wishlist is empty" text="Tap the heart on any card to save it here." /> : (
        <CardGrid testid="wishlist-grid">
          {items.map((it, i) => <CardTile key={it.card_id} index={i} card={{ id: it.card_id, name: it.name, image: it.image, localId: `${it.local_id} · ${it.set_name || ""}` }} owned={it.owned} price={it.price_usd} />)}
        </CardGrid>
      )}
    </div>
  );
}
