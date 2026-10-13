import { Link } from "react-router-dom";
import { Check, Plus } from "lucide-react";
import { cardImg, usd, vLabel } from "@/lib/api";

export const CardImage = ({ image, name, q = "low", className = "" }) =>
  image ? (
    <img src={cardImg(image, q)} alt={name} loading="lazy" className={`aspect-[63/88] w-full rounded-xl object-cover ${className}`} />
  ) : (
    <div className={`flex aspect-[63/88] w-full items-center justify-center rounded-xl bg-[linear-gradient(135deg,#1e3a8a,#3b82f6)] p-3 text-center font-display text-sm font-bold text-white ${className}`}>
      {name}
    </div>
  );

export function CardTile({ card, owned = 0, missing = false, price, variant, onQuickAdd, index = 0 }) {
  return (
    <div className="rise group relative" style={{ animationDelay: `${Math.min(index, 20) * 0.03}s` }} data-testid={`card-tile-${card.id}`}>
      <Link to={`/card/${card.id}`} className="block rounded-2xl border border-slate-200/60 bg-white p-2 shadow-[0_4px_12px_rgba(0,0,0,0.06)] transition-[transform,box-shadow] duration-300 hover:-translate-y-1.5 hover:shadow-[0_12px_24px_rgba(0,0,0,0.12)]">
        <div className={`holo rounded-xl ${missing ? "opacity-35 grayscale" : ""}`}>
          <CardImage image={card.image} name={card.name} />
        </div>
        <div className="px-1 pb-1 pt-2">
          <p className="truncate font-display text-sm font-bold">{card.name}</p>
          <div className="flex items-center justify-between text-xs text-slate-500">
            <span className="font-mono">#{card.localId ?? card.local_id}</span>
            {price != null && <span className="font-display font-bold text-slate-700">{usd(price)}</span>}
          </div>
          {variant && <span className="mt-1 inline-block rounded-full bg-[#FFCC00]/40 px-2 py-0.5 text-[10px] font-bold">{vLabel(variant)}</span>}
        </div>
      </Link>
      {owned > 0 && (
        <span data-testid={`owned-badge-${card.id}`} className="absolute right-3 top-3 flex items-center gap-0.5 rounded-full bg-emerald-500 px-2 py-0.5 text-xs font-black text-white shadow">
          <Check className="h-3 w-3" strokeWidth={3} /> {owned}
        </span>
      )}
      {onQuickAdd && (
        <button onClick={() => onQuickAdd(card)} data-testid={`quick-add-${card.id}`} aria-label="Add to collection"
          className="press absolute bottom-16 right-3 flex h-9 w-9 items-center justify-center rounded-full bg-[#E3350D] text-white opacity-90 shadow-[0_3px_0_#B02808] hover:opacity-100">
          <Plus className="h-5 w-5" strokeWidth={3} />
        </button>
      )}
    </div>
  );
}

export const CardGrid = ({ children, testid }) => (
  <div data-testid={testid} className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-5 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">{children}</div>
);
