import { useEffect, useState } from "react";
import { ResponsiveContainer, AreaChart, Area, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from "recharts";
import { api, usd, eur, vLabel } from "@/lib/api";

const COLORS = ["#E3350D", "#2563EB", "#F59E0B", "#10B981", "#8B5CF6"];
const short = (d) => d?.slice(5);

export function CollectionValueChart() {
  const [pts, setPts] = useState(null);
  useEffect(() => { api.get("/collection/history").then((r) => setPts(r.data)); }, []);
  if (!pts) return null;
  const first = pts[0]?.value_usd || 0, last = pts[pts.length - 1]?.value_usd || 0;
  const diff = last - first;
  return (
    <div className="rounded-3xl border border-slate-200/60 bg-white p-5 sm:p-6" data-testid="collection-value-chart">
      <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Collection value over time</p>
          <p className="font-display text-3xl font-black">{usd(last)} <span className="text-base text-slate-400">{eur(pts[pts.length - 1]?.value_eur)}</span></p>
        </div>
        {pts.length > 1 && <span className={`rounded-full px-3 py-1 text-sm font-bold ${diff >= 0 ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-600"}`} data-testid="collection-value-change">{diff >= 0 ? "+" : ""}{usd(diff)} since {pts[0].date}</span>}
      </div>
      {pts.length < 2 ? (
        <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">History started today. A new point is saved every day, so this chart fills in over time.</p>
      ) : (
        <div className="h-56">
          <ResponsiveContainer>
            <AreaChart data={pts} margin={{ left: 0, right: 8, top: 8 }}>
              <defs><linearGradient id="valFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#FFCC00" stopOpacity={0.6} /><stop offset="100%" stopColor="#FFCC00" stopOpacity={0} /></linearGradient></defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="date" tickFormatter={short} fontSize={12} />
              <YAxis tickFormatter={(v) => `$${v}`} fontSize={12} width={60} />
              <Tooltip formatter={(v) => usd(v)} />
              <Area type="monotone" dataKey="value_usd" name="Value (USD)" stroke="#E3350D" strokeWidth={3} fill="url(#valFill)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function CardPriceChart({ cardId }) {
  const [h, setH] = useState(null);
  useEffect(() => { api.get(`/cards/${cardId}/history`).then((r) => setH(r.data)).catch(() => setH(null)); }, [cardId]);
  if (!h) return null;
  const many = h.points.length > 1;
  const trend = h.cardmarket_trend;
  return (
    <div className="rounded-3xl border border-slate-200/60 bg-white p-5" data-testid="card-price-chart">
      <h2 className="mb-1 font-display text-xl font-bold">Price history</h2>
      <p className="mb-4 text-sm text-slate-500">{many ? "Daily TCGplayer market prices saved by PokéBinder." : "Cardmarket 30-day, 7-day, 1-day averages and today's trend. Daily history fills in as you use the app."}</p>
      <div className="h-56">
        <ResponsiveContainer>
          {many ? (
            <LineChart data={h.points} margin={{ left: 0, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="date" tickFormatter={short} fontSize={12} />
              <YAxis tickFormatter={(v) => `$${v}`} fontSize={12} width={55} />
              <Tooltip formatter={(v) => usd(v)} /><Legend />
              {h.variants.map((v, i) => <Line key={v} type="monotone" dataKey={`${v}_usd`} name={vLabel(v)} stroke={COLORS[i % 5]} strokeWidth={3} dot={false} connectNulls />)}
            </LineChart>
          ) : (
            <LineChart data={trend} margin={{ left: 0, right: 8, top: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" />
              <XAxis dataKey="date" tickFormatter={short} fontSize={12} />
              <YAxis tickFormatter={(v) => `€${v}`} fontSize={12} width={55} />
              <Tooltip formatter={(v) => eur(v)} /><Legend />
              <Line type="monotone" dataKey="normal" name="Normal (EUR)" stroke="#E3350D" strokeWidth={3} connectNulls />
              {trend.some((t) => t.holo) && <Line type="monotone" dataKey="holo" name="Holo / Reverse (EUR)" stroke="#2563EB" strokeWidth={3} connectNulls />}
            </LineChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
