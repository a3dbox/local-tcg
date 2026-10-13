import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { Gift, ArrowRightLeft, Target } from "lucide-react";
import { toast } from "sonner";
import confetti from "canvas-confetti";
import { api, cardImg, formatErr, gbp, vLabel } from "@/lib/api";
import { PageTitle, Spinner, Empty, Btn, Chips } from "@/components/UI";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";

function TradeCard({ c, onGive, testid }) {
  return (
    <div className="rise relative rounded-2xl border border-slate-200/60 bg-white p-2 shadow-[0_4px_12px_rgba(0,0,0,0.06)]" data-testid={testid}>
      {c.needed_for_goal && <span className="absolute left-3 top-3 z-10 flex items-center gap-1 rounded-full bg-[#FFCC00] px-2 py-0.5 text-[10px] font-black"><Target className="h-3 w-3" /> Goal</span>}
      <Link to={`/card/${c.card_id}`}><img src={cardImg(c.image)} alt={c.name} loading="lazy" className="aspect-[63/88] w-full rounded-xl object-cover" /></Link>
      <p className="mt-2 truncate font-display text-sm font-bold">{c.name}</p>
      <p className="truncate text-xs text-slate-500">{c.set_name} · #{c.local_id}</p>
      <div className="mt-1 flex items-center justify-between text-xs"><span className="font-bold text-emerald-600">{c.spare_qty} spare</span><span className="font-bold">{gbp(c.price_gbp)}</span></div>
      {onGive && <Btn onClick={() => onGive(c)} className="mt-2 w-full px-3 py-1.5 text-sm" data-testid={`${testid}-give`}><Gift className="h-4 w-4" /> Give</Btn>}
    </div>
  );
}

const Grid = ({ children, testid }) => <div data-testid={testid} className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">{children}</div>;

export default function Family() {
  const [members, setMembers] = useState(null);
  const [sel, setSel] = useState("");
  const [cmp, setCmp] = useState(null);
  const [giving, setGiving] = useState(null);
  const [log, setLog] = useState([]);
  useEffect(() => {
    api.get("/family/members").then((r) => { setMembers(r.data); if (r.data[0]) setSel(r.data[0].id); });
  }, []);
  const load = useCallback(() => {
    api.get("/family/activity").then((r) => setLog(r.data));
    if (sel) { setCmp(null); api.get(`/family/compare/${sel}`).then((r) => setCmp(r.data)); }
  }, [sel]);
  useEffect(() => { load(); }, [load]);

  const give = async () => {
    const c = giving;
    setGiving(null);
    try {
      await api.post("/family/give", { to_user_id: sel, card_id: c.card_id, variant: c.spare_variant, quantity: 1 });
      toast.success(`Gave ${c.name} to ${cmp.other.name}!`);
      if (c.needed_for_goal) confetti({ particleCount: 120, spread: 80 });
      load();
    } catch (e) { toast.error(formatErr(e)); }
  };

  if (!members) return <Spinner />;
  return (
    <div data-testid="family-page">
      <PageTitle title="Family trading" sub="Compare binders, spot duplicates and give spare cards to each other." />
      {members.length === 0 ? (
        <Empty testid="family-empty" title="No other trainers yet" text="Create another account (log out → Create account) for each family member, then come back here." />
      ) : (
        <>
          <Chips testid="family-member-chips" options={members.map((m) => ({ value: m.id, label: m.name }))} value={sel} onChange={(v) => v && setSel(v)} />
          {!cmp ? <Spinner /> : (
            <div className="mt-6 space-y-10">
              <div className="grid grid-cols-3 gap-3 sm:gap-6" data-testid="family-counts">
                {[["Both have", cmp.counts.shared], ["Only you", cmp.counts.only_me], [`Only ${cmp.other.name}`, cmp.counts.only_them]].map(([k, v]) => (
                  <div key={k} className="rounded-3xl bg-white p-4 text-center shadow-sm sm:p-6"><p className="font-display text-3xl font-black">{v}</p><p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">{k}</p></div>
                ))}
              </div>
              <section>
                <h2 className="mb-1 flex items-center gap-2 font-display text-2xl font-bold"><Gift className="h-6 w-6 text-[#E3350D]" /> You can give {cmp.other.name}</h2>
                <p className="mb-4 text-sm text-slate-500">Your duplicates that {cmp.other.name} doesn't have yet. "Goal" means it's in a set they're tracking.</p>
                {cmp.i_can_give.length === 0 ? <p className="rounded-2xl bg-white p-5 text-slate-500">No spare cards they're missing.</p> : (
                  <Grid testid="i-can-give-grid">{cmp.i_can_give.map((c) => <TradeCard key={c.card_id} c={c} onGive={setGiving} testid={`give-card-${c.card_id}`} />)}</Grid>
                )}
              </section>
              <section>
                <h2 className="mb-1 flex items-center gap-2 font-display text-2xl font-bold"><ArrowRightLeft className="h-6 w-6 text-[#2563EB]" /> {cmp.other.name} can give you</h2>
                <p className="mb-4 text-sm text-slate-500">Their duplicates that you're missing — ask nicely!</p>
                {cmp.they_can_give.length === 0 ? <p className="rounded-2xl bg-white p-5 text-slate-500">Nothing to swap from them right now.</p> : (
                  <Grid testid="they-can-give-grid">{cmp.they_can_give.map((c) => <TradeCard key={c.card_id} c={c} testid={`receive-card-${c.card_id}`} />)}</Grid>
                )}
              </section>
            </div>
          )}
          {log.length > 0 && (
            <section className="mt-10">
              <h2 className="mb-3 font-display text-xl font-bold">Recent gifts</h2>
              <div className="space-y-2" data-testid="family-activity">
                {log.map((l, i) => (
                  <div key={i} className="flex items-center gap-3 rounded-2xl bg-white p-2 pr-4">
                    <img src={cardImg(l.image)} alt="" className="h-14 w-10 rounded object-cover" />
                    <p className="text-sm"><b>{l.from_name}</b> gave <b>{l.name}</b> ({vLabel(l.variant)}) to <b>{l.to_name}</b></p>
                    <span className="ml-auto text-xs text-slate-400">{l.created_at.slice(0, 10)}</span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </>
      )}
      <AlertDialog open={!!giving} onOpenChange={(o) => !o && setGiving(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Give {giving?.name} to {cmp?.other.name}?</AlertDialogTitle>
            <AlertDialogDescription>One {vLabel(giving?.spare_variant)} copy moves from your collection to theirs.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="give-cancel-button">Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={give} className="bg-[#E3350D] hover:bg-[#C82D0A]" data-testid="give-confirm-button">Give card</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
