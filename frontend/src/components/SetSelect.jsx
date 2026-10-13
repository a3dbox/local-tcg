import { useState } from "react";
import { logoImg } from "@/lib/api";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function SetIcon({ set }) {
  const [src, setSrc] = useState(set.icon || logoImg(set.logo));
  if (!src) return <span className="inline-block h-5 w-8" />;
  return (
    <img src={src} alt="" loading="lazy" data-testid={`set-icon-${set.id}`} className="inline-block h-5 w-8 shrink-0 object-contain"
      onError={() => setSrc(src === set.icon && set.logo ? logoImg(set.logo) : null)} />
  );
}

export function SetSelect({ sets, value, onChange, placeholder, testid, allowAll = true, className = "sm:w-64" }) {
  return (
    <Select value={value || (allowAll ? "all" : "")} onValueChange={(v) => onChange(v === "all" ? "" : v)}>
      <SelectTrigger className={`h-11 w-full rounded-full border-slate-200 bg-white font-semibold ${className}`} data-testid={testid}><SelectValue placeholder={placeholder} /></SelectTrigger>
      <SelectContent className="max-h-80">
        {allowAll && <SelectItem value="all">{placeholder}</SelectItem>}
        {sets.map((s) => (
          <SelectItem key={s.id} value={s.id} data-testid={`${testid}-option-${s.id}`}>
            <span className="flex items-center gap-2"><SetIcon set={s} /> {s.name}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
