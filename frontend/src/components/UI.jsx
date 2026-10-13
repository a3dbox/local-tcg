export function ProgressBar({ value = 0, total = 0, label, testid, size = "h-4" }) {
  const pct = total ? Math.round((value / total) * 100) : 0;
  return (
    <div data-testid={testid}>
      {label && (
        <div className="mb-1 flex items-baseline justify-between">
          <span className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">{label}</span>
          <span className="font-display text-sm font-bold">
            {value}/{total} <span className="text-slate-400">· {pct}%</span>
          </span>
        </div>
      )}
      <div className={`${size} w-full overflow-hidden rounded-full bg-slate-100`}>
        <div className={`h-full rounded-full transition-[width] duration-700 ${pct >= 100 ? "bg-emerald-500" : "bg-gradient-to-r from-[#FFCC00] to-[#E3350D]"}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function Chips({ options, value, onChange, testid, colors }) {
  return (
    <div className="no-scrollbar flex gap-2 overflow-x-auto pb-1" data-testid={testid}>
      {options.map((o) => {
        const v = typeof o === "string" ? o : o.value;
        const l = typeof o === "string" ? o : o.label;
        const active = value === v;
        return (
          <button key={v || "all"} onClick={() => onChange(active ? "" : v)} data-testid={`${testid}-${(v || "all").toLowerCase().replace(/\s+/g, "-")}`}
            className={`press shrink-0 rounded-full border px-4 py-1.5 text-sm font-bold ${active ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"}`}>
            {colors?.[v] && <span className="mr-1.5 inline-block h-2.5 w-2.5 rounded-full" style={{ background: colors[v] }} />}
            {l}
          </button>
        );
      })}
    </div>
  );
}

export const PageTitle = ({ title, sub, children }) => (
  <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">{title}</h1>
      {sub && <p className="mt-2 text-base text-slate-600 md:text-lg">{sub}</p>}
    </div>
    {children}
  </div>
);

export const Empty = ({ title, text, children, testid }) => (
  <div data-testid={testid} className="rounded-3xl border-2 border-dashed border-slate-200 bg-white/60 p-10 text-center">
    <p className="font-display text-2xl font-bold">{title}</p>
    <p className="mx-auto mt-2 max-w-md text-slate-600">{text}</p>
    <div className="mt-5 flex justify-center gap-3">{children}</div>
  </div>
);

export const Spinner = ({ text = "Loading…" }) => (
  <div className="flex items-center justify-center gap-3 py-16 text-slate-500" data-testid="loading-spinner">
    <div className="h-6 w-6 animate-spin rounded-full border-[3px] border-slate-200 border-t-[#E3350D]" />
    <span className="font-display font-semibold">{text}</span>
  </div>
);

export const Btn = ({ variant = "primary", className = "", ...p }) => {
  const v = {
    primary: "bg-[#E3350D] text-white shadow-[0_4px_0_#B02808] hover:bg-[#C82D0A]",
    yellow: "bg-[#FFCC00] text-slate-900 shadow-[0_4px_0_#C9A200] hover:bg-[#E6B800]",
    ghost: "border border-slate-200 bg-white text-slate-700 hover:border-slate-400",
    dark: "bg-slate-900 text-white shadow-[0_4px_0_#000] hover:bg-slate-800",
  }[variant];
  return <button {...p} className={`press inline-flex items-center justify-center gap-2 rounded-full px-5 py-2.5 font-display font-bold disabled:opacity-50 ${v} ${className}`} />;
};
