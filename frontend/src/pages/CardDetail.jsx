import { useEffect, useState, useCallback } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Heart, Minus, Plus, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import confetti from "canvas-confetti";
import { api, formatErr, usd, eur, gbp, vLabel, TYPE_COLORS, logoImg } from "@/lib/api";
import { CardImage, CardTile, CardGrid } from "@/components/CardTile";
import { Spinner, Btn } from "@/components/UI";
import { CardPriceChart } from "@/components/Charts";
import { MoveSelect } from "@/pages/Storage";

function WherePanel({ where, locations, onMoved }) {
  if (!where?.length) return null;
  return (
    <div className="mt-4 rounded-2xl bg-white p-3" data-testid="where-panel">
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Where are my copies?</p>
      {where.map((w) => (
        <div key={`${w.item_id}-${w.location_id}`} className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 py-1.5 text-sm last:border-0" data-testid={`where-row-${w.location_id}-${w.variant}`}>
          <span><b>{w.quantity}×</b> {vLabel(w.variant)} · <span className={w.location_id === "unassigned" ? "text-slate-400" : "font-bold"}>{w.name}</span></span>
          <MoveSelect item={w} from={w.location_id} locations={locations} onMoved={onMoved} testid={`where-move-${w.location_id}-${w.variant}`} />
        </div>
      ))}
    </div>
  );
}

function AddToCustomSet({ cardId }) {
  const [sets, setSets] = useState([]);
  useEffect(() => { api.get("/custom-sets").then((r) => setSets(r.data)); }, []);
  if (!sets.length) return <Link to="/my-sets" className="text-sm font-bold text-[#E3350D]" data-testid="create-custom-set-link">+ Create a custom set</Link>;
  const add = async (sid) => { if (!sid) return; await api.post(`/custom-sets/${sid}/cards`, { card_id: cardId }); toast.success(`Added to ${sets.find((s) => s.id === sid).name}`); };
  return (
    <select value="" onChange={(e) => add(e.target.value)} className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-bold" data-testid="add-to-custom-set-select">
      <option value="">+ Add to my set…</option>{sets.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
    </select>
  );
}

const Row = ({ k, v }) => v == null || v === "" ? null : (
  <div className="flex justify-between gap-4 border-b border-slate-100 py-2 text-sm"><span className="text-slate-500">{k}</span><span className="text-right font-bold">{v}</span></div>
);

function VariantRow({ v, onSet }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-2xl border border-slate-200/70 bg-white p-3" data-testid={`variant-row-${v.type}`}>
      <div className="min-w-0">
        <p className="font-display font-bold">{v.label}</p>
        <p className="text-sm text-slate-500"><span className="font-bold text-slate-800">{gbp(v.price_gbp)}</span> <span className="text-xs">({usd(v.price_usd)} · {eur(v.price_eur)})</span></p>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={() => onSet(v, v.owned - 1)} disabled={!v.owned} className="press flex h-10 w-10 items-center justify-center rounded-full border border-slate-200 disabled:opacity-30" data-testid={`variant-minus-${v.type}`}><Minus className="h-4 w-4" strokeWidth={3} /></button>
        <span className="w-8 text-center font-display text-xl font-black" data-testid={`variant-qty-${v.type}`}>{v.owned}</span>
        <button onClick={() => onSet(v, v.owned + 1)} className="press flex h-10 w-10 items-center justify-center rounded-full bg-[#E3350D] text-white shadow-[0_3px_0_#B02808]" data-testid={`variant-plus-${v.type}`}><Plus className="h-4 w-4" strokeWidth={3} /></button>
      </div>
    </div>
  );
}

function PriceTables({ pricing, fx }) {
  const fu = (v) => (v == null || !fx?.usd_gbp ? null : v * fx.usd_gbp);
  const fe = (v) => (v == null || !fx?.eur_gbp ? null : v * fx.eur_gbp);
  const both = (v) => (v == null ? null : `${gbp(fe(v))} (${eur(v)})`);
  const tp = pricing?.tcgplayer || {};
  const cm = pricing?.cardmarket;
  const tpRows = Object.entries(tp).filter(([, e]) => e && typeof e === "object");
  if (!tpRows.length && !cm) return <p className="text-sm text-slate-500">No price data available for this card yet.</p>;
  return (
    <div className="grid gap-4 md:grid-cols-2" data-testid="price-tables">
      {tpRows.length > 0 && (
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-slate-500">TCGplayer · converted to GBP</p>
          {tpRows.map(([k, e]) => (
            <div key={k} className="mb-2"><p className="font-display text-sm font-bold capitalize">{k.replace(/-/g, " ")}</p>
              <div className="grid grid-cols-4 gap-1 text-center text-xs">
                {[["Low", e.lowPrice], ["Mid", e.midPrice], ["High", e.highPrice], ["Market", e.marketPrice]].map(([l, p]) => (
                  <div key={l} className="rounded-lg bg-white p-1.5"><p className="text-slate-500">{l}</p><p className="font-bold">{gbp(fu(p))}</p><p className="text-[10px] text-slate-400">{usd(p)}</p></div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
      {cm && (
        <div className="rounded-2xl bg-slate-50 p-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Cardmarket · converted to GBP</p>
          <Row k="Trend" v={both(cm.trend)} /><Row k="Average" v={both(cm.avg)} /><Row k="Lowest" v={both(cm.low)} />
          <Row k="7-day avg" v={both(cm.avg7)} /><Row k="30-day avg" v={both(cm.avg30)} />
          {cm["trend-holo"] ? <Row k="Holo / Reverse trend" v={both(cm["trend-holo"])} /> : null}
        </div>
      )}
    </div>
  );
}

export default function CardDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState(null);
  const [prints, setPrints] = useState([]);
  const [locations, setLocations] = useState([]);
  useEffect(() => { api.get("/locations").then((r) => setLocations(r.data.locations)); }, []);
  const load = useCallback(() => api.get(`/cards/${id}`).then((r) => setD(r.data)).catch((e) => toast.error(formatErr(e))), [id]);
  useEffect(() => { setD(null); load(); }, [load]);
  useEffect(() => {
    if (!d) return;
    api.get("/cards", { params: { q: d.card.name, exact: true, size: 60 } }).then((r) => setPrints(r.data.items.filter((c) => c.id !== id)));
  }, [d?.card?.name, id]); // eslint-disable-line

  if (!d) return <Spinner text="Loading card…" />;
  const c = d.card;
  const setQty = async (v, q) => {
    try {
      await api.post("/collection/set-qty", { card_id: id, variant: v.type, quantity: Math.max(0, q) });
      if (q > v.owned) { toast.success(`Added ${c.name} (${v.label})`); if (q === 1 && (v.price_gbp || 0) > 15) confetti({ particleCount: 120, spread: 80 }); }
      load();
    } catch (e) { toast.error(formatErr(e)); }
  };
  const toggleWish = async () => {
    const { data } = await api.post(`/wishlist/${id}`);
    toast(data.wishlisted ? "Added to wishlist" : "Removed from wishlist");
    load();
  };
  const totalOwned = d.variants.reduce((a, v) => a + v.owned, 0);

  return (
    <div data-testid="card-detail-page">
      <button onClick={() => nav(-1)} className="mb-6 flex items-center gap-2 font-display font-bold text-slate-600 hover:text-[#E3350D]" data-testid="back-button"><ArrowLeft className="h-5 w-5" /> Back</button>
      <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr] lg:gap-12">
        <div className="rise">
          <div className="holo rounded-[20px] shadow-[0_20px_50px_rgba(0,0,0,0.25)]"><CardImage image={c.image} name={c.name} q="high" className="rounded-[20px]" /></div>
        </div>
        <div className="rise space-y-6" style={{ animationDelay: ".08s" }}>
          <div>
            <Link to={`/sets/${c.set?.id}`} className="inline-flex items-center gap-2 text-sm font-bold text-slate-500 hover:text-[#E3350D]" data-testid="card-set-link">
              {c.set?.symbol && <img src={`${c.set.symbol}.png`} alt="" onError={(e) => { e.currentTarget.style.display = "none"; }} className="h-5 w-5 object-contain" />} {c.set?.name}
            </Link>
            <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl" data-testid="card-name">{c.name}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <span className="rounded-full bg-slate-900 px-3 py-1 font-mono text-sm font-bold text-white" data-testid="card-number">#{c.localId}/{c.set?.cardCount?.official}</span>
              {c.rarity && <span className="rounded-full bg-[#FFCC00] px-3 py-1 text-sm font-bold">{c.rarity}</span>}
              {(c.types || []).map((t) => <span key={t} className="rounded-full px-3 py-1 text-sm font-bold" style={{ background: TYPE_COLORS[t] || "#e2e8f0" }}>{t}</span>)}
              {c.hp && <span className="rounded-full border border-slate-300 px-3 py-1 text-sm font-bold">{c.hp} HP</span>}
            </div>
          </div>
          <div className="rounded-3xl border border-slate-200/60 bg-[#FDFBF7] p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="font-display text-lg font-bold">My copies <span className="text-slate-400">({totalOwned})</span></p>
              <Btn variant={d.wishlisted ? "yellow" : "ghost"} onClick={toggleWish} className="px-4 py-2 text-sm" data-testid="wishlist-toggle-button">
                <Heart className="h-4 w-4" fill={d.wishlisted ? "currentColor" : "none"} /> {d.wishlisted ? "On wishlist" : "Wishlist"}
              </Btn>
            </div>
            <div className="space-y-2">{d.variants.map((v) => <VariantRow key={v.type} v={v} onSet={setQty} />)}</div>
            <WherePanel where={d.where} locations={locations} onMoved={load} />
            <div className="mt-4"><AddToCustomSet cardId={id} /></div>
          </div>
          <div><h2 className="mb-3 font-display text-xl font-bold">Prices</h2><PriceTables pricing={c.pricing} fx={d.fx} /></div>
          <CardPriceChart cardId={id} />
          <div className="grid gap-6 md:grid-cols-2">
            <div className="rounded-3xl bg-white p-5">
              <h2 className="mb-2 font-display text-xl font-bold">Details</h2>
              <Row k="Category" v={c.category} /><Row k="Stage" v={c.stage} /><Row k="Evolves from" v={c.evolveFrom} />
              <Row k="Illustrator" v={c.illustrator} /><Row k="Regulation mark" v={c.regulationMark} />
              <Row k="Retreat" v={c.retreat} /><Row k="Weakness" v={(c.weaknesses || []).map((w) => `${w.type} ${w.value}`).join(", ")} />
              <Row k="Standard legal" v={c.legal ? (c.legal.standard ? "Yes" : "No") : null} />
              {c.dexId?.[0] && <Link to={`/pokedex/${c.dexId[0]}`} className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-[#E3350D]" data-testid="card-pokedex-link">All cards of this Pokémon <ExternalLink className="h-3 w-3" /></Link>}
            </div>
            <div className="rounded-3xl bg-white p-5">
              <h2 className="mb-2 font-display text-xl font-bold">Moves & text</h2>
              {(c.abilities || []).map((a) => <div key={a.name} className="mb-3"><p className="font-bold text-[#E3350D]">{a.type}: {a.name}</p><p className="text-sm text-slate-600">{a.effect}</p></div>)}
              {(c.attacks || []).map((a) => <div key={a.name} className="mb-3"><p className="font-bold">{a.name} <span className="float-right font-display">{a.damage}</span></p>{a.effect && <p className="text-sm text-slate-600">{a.effect}</p>}</div>)}
              {c.effect && <p className="text-sm text-slate-600">{c.effect}</p>}
              {c.description && <p className="text-sm italic text-slate-500">{c.description}</p>}
            </div>
          </div>
        </div>
      </div>
      {prints.length > 0 && (
        <section className="mt-12"><h2 className="mb-4 font-display text-2xl font-bold">Other printings of {c.name}</h2>
          <CardGrid testid="other-prints-grid">{prints.map((p, i) => <CardTile key={p.id} card={p} owned={p.owned} index={i} />)}</CardGrid>
        </section>
      )}
    </div>
  );
}
