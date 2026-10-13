import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cardImg, gbp } from "@/lib/api";

const useWide = () => {
  const [wide, setWide] = useState(() => window.innerWidth >= 1024);
  useEffect(() => {
    const f = () => setWide(window.innerWidth >= 1024);
    window.addEventListener("resize", f);
    return () => window.removeEventListener("resize", f);
  }, []);
  return wide;
};

function Pocket({ card, owned, price }) {
  if (!card) return <div className="aspect-[63/88] rounded-lg border border-dashed border-slate-300/60 bg-slate-100/40" />;
  return (
    <Link to={`/card/${card.id}`} data-testid={`binder-pocket-${card.id}`} className="group relative block aspect-[63/88] overflow-hidden rounded-lg border border-white/70 bg-white/40 shadow-[inset_0_2px_6px_rgba(0,0,0,0.12)]">
      {card.image && <img src={cardImg(card.image)} alt={card.name} loading="lazy" className={`h-full w-full object-cover transition-transform group-hover:scale-[1.03] ${owned ? "" : "opacity-[0.12] grayscale"}`} />}
      {!owned && (
        <div className="absolute inset-0 flex flex-col items-center justify-center p-1 text-center">
          <span className="font-mono text-sm font-bold text-slate-500">#{card.localId}</span>
          <span className="line-clamp-2 font-display text-[11px] font-bold text-slate-600">{card.name}</span>
          {price != null && <span className="mt-0.5 text-[10px] font-bold text-slate-400">{gbp(price)}</span>}
        </div>
      )}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(120deg,transparent_40%,rgba(255,255,255,0.35)_50%,transparent_60%)]" />
      {owned > 1 && <span className="absolute right-1 top-1 rounded-full bg-emerald-500 px-1.5 text-[10px] font-black text-white">x{owned}</span>}
    </Link>
  );
}

const Page = ({ cards, owned, details, side }) => (
  <div className={`grid flex-1 grid-cols-3 gap-2 bg-[#FBF8F1] p-3 sm:gap-3 sm:p-4 ${side === "left" ? "rounded-l-xl" : "rounded-r-xl"} rounded-xl lg:rounded-none ${side === "left" ? "lg:rounded-l-xl" : "lg:rounded-r-xl"}`}>
    {Array.from({ length: 9 }).map((_, i) => {
      const c = cards[i];
      return <Pocket key={c?.id || `empty-${i}`} card={c} owned={c ? Object.values(owned[c.id] || {}).reduce((a, b) => a + b, 0) : 0} price={c && details?.[c.id]?.price_gbp} />;
    })}
  </div>
);

export function Binder({ cards, owned, details }) {
  const wide = useWide();
  const per = wide ? 18 : 9;
  const total = Math.max(1, Math.ceil(cards.length / per));
  const [[spread, dir], setSpread] = useState([0, 1]);
  const go = useCallback((d) => setSpread(([s]) => [Math.min(total - 1, Math.max(0, s + d)), d]), [total]);
  useEffect(() => { setSpread(([s]) => [Math.min(s, total - 1), 1]); }, [total]);
  useEffect(() => {
    const k = (e) => { if (e.key === "ArrowRight") go(1); if (e.key === "ArrowLeft") go(-1); };
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [go]);
  const [touch, setTouch] = useState(null);
  const slice = cards.slice(spread * per, spread * per + per);
  const pages = wide ? [slice.slice(0, 9), slice.slice(9, 18)] : [slice];
  const ownedOnSpread = slice.filter((c) => owned[c.id]).length;
  const p1 = spread * (wide ? 2 : 1) + 1;

  return (
    <div data-testid="binder-view" className="mx-auto max-w-4xl select-none">
      <div className="rounded-[28px] bg-[#2B2F3A] p-3 shadow-[0_24px_60px_rgba(0,0,0,0.35)] sm:p-5" style={{ perspective: 1800 }}
        onTouchStart={(e) => setTouch(e.touches[0].clientX)} onTouchEnd={(e) => { if (touch == null) return; const dx = e.changedTouches[0].clientX - touch; if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1); setTouch(null); }}>
        <AnimatePresence mode="wait" initial={false} custom={dir}>
          <motion.div key={spread} custom={dir} className="flex gap-0 lg:gap-1" style={{ transformOrigin: dir > 0 ? "left center" : "right center" }}
            initial={{ rotateY: dir > 0 ? 70 : -70, opacity: 0 }} animate={{ rotateY: 0, opacity: 1 }} exit={{ rotateY: dir > 0 ? -70 : 70, opacity: 0 }}
            transition={{ duration: 0.35, ease: "easeOut" }}>
            {pages.map((pc, i) => (
              <div key={i} className="relative flex flex-1">
                <Page cards={pc} owned={owned} details={details} side={i === 0 ? "left" : "right"} />
                {wide && i === 0 && <div className="absolute -right-1 top-0 z-10 h-full w-2 bg-gradient-to-r from-black/20 via-black/5 to-transparent" />}
              </div>
            ))}
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="mt-5 flex items-center justify-between gap-3">
        <button onClick={() => go(-1)} disabled={spread === 0} data-testid="binder-prev-button" className="press flex h-12 w-12 items-center justify-center rounded-full bg-white shadow disabled:opacity-30"><ChevronLeft className="h-6 w-6" strokeWidth={3} /></button>
        <div className="text-center">
          <p className="font-display text-lg font-black" data-testid="binder-page-indicator">Page {p1}{wide && pages[1]?.length ? `–${p1 + 1}` : ""} of {Math.ceil(cards.length / 9)}</p>
          <p className="text-sm text-slate-500">{ownedOnSpread}/{slice.length} collected on these pages · swipe or use ← →</p>
        </div>
        <button onClick={() => go(1)} disabled={spread >= total - 1} data-testid="binder-next-button" className="press flex h-12 w-12 items-center justify-center rounded-full bg-[#E3350D] text-white shadow-[0_4px_0_#B02808] disabled:opacity-30"><ChevronRight className="h-6 w-6" strokeWidth={3} /></button>
      </div>
    </div>
  );
}
