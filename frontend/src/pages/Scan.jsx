import { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Camera, Upload, Zap, Trash2, Check, Images, Minus, Plus, ExternalLink } from "lucide-react";
import { toast } from "sonner";
import confetti from "canvas-confetti";
import { api, formatErr, cardImg, usd, vLabel } from "@/lib/api";
import { Btn } from "@/components/UI";

const GUIDE_H = 0.82;
const RATIO = 63 / 88;

function useCamera(videoRef) {
  const [state, setState] = useState("idle");
  useEffect(() => {
    let stream;
    if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) { setState("unsupported"); return; }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1440 } }, audio: false })
      .then((s) => { stream = s; if (videoRef.current) { videoRef.current.srcObject = s; videoRef.current.play().catch(() => {}); } setState("ready"); })
      .catch(() => setState("denied"));
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, [videoRef]);
  return state;
}

function grabFrame(video) {
  const vw = video.videoWidth, vh = video.videoHeight, cw = video.clientWidth, ch = video.clientHeight;
  if (!vw || !cw) return null;
  const scale = Math.max(cw / vw, ch / vh);
  const ox = (vw - cw / scale) / 2, oy = (vh - ch / scale) / 2;
  const gh = Math.min(ch, ch * GUIDE_H * 1.1), gw = Math.min(cw, gh * RATIO);
  const sx = ox + (cw - gw) / 2 / scale, sy = oy + (ch - gh) / 2 / scale, sw = gw / scale, sh = gh / scale;
  const out = Math.min(1, 1400 / sh);
  const c = document.createElement("canvas");
  c.width = Math.round(sw * out); c.height = Math.round(sh * out);
  c.getContext("2d").drawImage(video, sx, sy, sw, sh, 0, 0, c.width, c.height);
  return new Promise((res) => c.toBlob(res, "image/jpeg", 0.9));
}

async function recognise(blob) {
  const fd = new FormData();
  fd.append("file", blob, "scan.jpg");
  const { data } = await api.post("/scan", fd, { timeout: 120000 });
  return data;
}

function QueueItem({ it, onChange, onRemove }) {
  const m = it.matches?.[it.sel];
  return (
    <div className="rise flex gap-3 rounded-2xl border border-slate-200/70 bg-white p-3" data-testid={`batch-item-${it.key}`}>
      <img src={it.thumb} alt="scan" className="h-24 w-[68px] shrink-0 rounded-lg object-cover" />
      {m ? <img src={cardImg(m.image)} alt={m.name} className="h-24 w-[68px] shrink-0 rounded-lg object-cover" /> : <div className="h-24 w-[68px] shrink-0 rounded-lg bg-slate-100" />}
      <div className="min-w-0 flex-1">
        {it.status === "scanning" && <p className="animate-pulse font-display font-bold text-slate-500">Recognising…</p>}
        {it.status === "error" && <p className="font-bold text-red-600">Scan failed</p>}
        {it.status === "done" && !m && <p className="font-bold text-amber-600">No match — try again</p>}
        {m && (
          <>
            <p className="truncate font-display font-bold">{m.name}</p>
            <p className="truncate text-xs text-slate-500">{m.set_name} · #{m.local_id} · {usd(m.price_usd)}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <select value={it.sel} onChange={(e) => onChange({ sel: Number(e.target.value), variant: it.matches[e.target.value].variants?.[0] || "normal" })}
                className="max-w-[170px] rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold" data-testid={`batch-item-match-${it.key}`}>
                {it.matches.map((x, i) => <option key={x.card_id} value={i}>{`${x.name} · ${x.set_name} #${x.local_id}`}</option>)}
              </select>
              <select value={it.variant} onChange={(e) => onChange({ variant: e.target.value })} className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-xs font-semibold" data-testid={`batch-item-variant-${it.key}`}>
                {(m.variants || ["normal", "holo", "reverse"]).map((v) => <option key={v} value={v}>{vLabel(v)}</option>)}
              </select>
              <div className="flex items-center gap-1">
                <button onClick={() => onChange({ qty: Math.max(1, it.qty - 1) })} className="rounded-full border p-1"><Minus className="h-3 w-3" /></button>
                <span className="w-5 text-center text-sm font-black">{it.qty}</span>
                <button onClick={() => onChange({ qty: it.qty + 1 })} className="rounded-full border p-1"><Plus className="h-3 w-3" /></button>
              </div>
            </div>
            {it.confidence !== "high" && <p className="mt-1 text-[11px] font-bold text-amber-600">Check this one — {it.confidence} confidence</p>}
          </>
        )}
      </div>
      <button onClick={onRemove} className="self-start rounded-full p-2 text-slate-400 hover:bg-red-50 hover:text-red-600" data-testid={`batch-item-remove-${it.key}`}><Trash2 className="h-4 w-4" /></button>
    </div>
  );
}

function SingleResult({ res, onAdd }) {
  if (!res) return null;
  if (!res.matches.length) return <p className="rounded-2xl bg-amber-50 p-4 font-semibold text-amber-700" data-testid="scan-no-match">Couldn't recognise that card. Fill the frame with the card, avoid glare, and try again.</p>;
  return (
    <div className="space-y-3" data-testid="scan-result">
      <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Best matches · {res.confidence} confidence {res.ocr?.numbers?.length ? `· read ${res.ocr.numbers[0]}` : ""}</p>
      {res.matches.map((m, i) => (
        <div key={m.card_id} className={`flex items-center gap-3 rounded-2xl border bg-white p-2 ${i === 0 ? "border-[#E3350D]" : "border-slate-200"}`} data-testid={`scan-match-${i}`}>
          <img src={cardImg(m.image)} alt={m.name} className="h-20 w-14 rounded-lg object-cover" />
          <div className="min-w-0 flex-1"><p className="truncate font-display font-bold">{m.name}</p><p className="truncate text-xs text-slate-500">{m.set_name} · #{m.local_id}</p></div>
          <Link to={`/card/${m.card_id}`} className="rounded-full p-2 hover:bg-slate-100" data-testid={`scan-match-open-${i}`}><ExternalLink className="h-4 w-4" /></Link>
          <button onClick={() => onAdd(m)} className="press rounded-full bg-[#E3350D] p-2 text-white" data-testid={`scan-match-add-${i}`}><Plus className="h-4 w-4" strokeWidth={3} /></button>
        </div>
      ))}
    </div>
  );
}

export default function Scan() {
  const nav = useNavigate();
  const videoRef = useRef(null);
  const cam = useCamera(videoRef);
  const [mode, setMode] = useState("single");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState(null);
  const [queue, setQueue] = useState([]);
  const [auto, setAuto] = useState(false);
  const [autoOpen, setAutoOpen] = useState(true);
  const last = useRef({ id: null, t: 0 });
  const busyRef = useRef(false);

  const patch = (key, p) => setQueue((q) => q.map((x) => (x.key === key ? { ...x, ...p } : x)));

  const processBlob = useCallback(async (blob) => {
    if (mode === "single") {
      setBusy(true); setRes(null);
      try {
        const r = await recognise(blob);
        setRes(r);
        if (autoOpen && r.confidence === "high") nav(`/card/${r.matches[0].card_id}`);
      } catch (e) { toast.error(formatErr(e)); } finally { setBusy(false); }
      return;
    }
    const key = `${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    setQueue((q) => [{ key, thumb: URL.createObjectURL(blob), status: "scanning", matches: [], sel: 0, qty: 1, variant: "normal" }, ...q]);
    try {
      const r = await recognise(blob);
      const top = r.matches[0];
      if (top && auto && top.card_id === last.current.id && Date.now() - last.current.t < 8000) {
        setQueue((q) => q.filter((x) => x.key !== key));
        return;
      }
      if (top) { last.current = { id: top.card_id, t: Date.now() }; navigator.vibrate?.(40); }
      patch(key, { status: "done", matches: r.matches, confidence: r.confidence, variant: top?.variants?.[0] || "normal" });
    } catch { patch(key, { status: "error" }); }
  }, [mode, auto, autoOpen, nav]);

  const capture = useCallback(async () => {
    if (busyRef.current || !videoRef.current) return;
    busyRef.current = true;
    try { const b = await grabFrame(videoRef.current); if (b) await processBlob(b); } finally { busyRef.current = false; }
  }, [processBlob]);

  useEffect(() => {
    if (!(mode === "batch" && auto && cam === "ready")) return;
    const t = setInterval(capture, 2200);
    return () => clearInterval(t);
  }, [mode, auto, cam, capture]);

  const onFiles = async (e) => {
    const files = [...e.target.files];
    e.target.value = "";
    for (const f of mode === "single" ? files.slice(0, 1) : files) await processBlob(f);
  };
  const addOne = async (m) => {
    try { await api.post("/collection/add", { card_id: m.card_id, variant: m.variants?.[0] || "normal" }); toast.success(`Added ${m.name}`); } catch (e) { toast.error(formatErr(e)); }
  };
  const ready = queue.filter((x) => x.status === "done" && x.matches[x.sel]);
  const addAll = async () => {
    try {
      const { data } = await api.post("/collection/batch", { items: ready.map((x) => ({ card_id: x.matches[x.sel].card_id, variant: x.variant, quantity: x.qty })) });
      toast.success(`Added ${data.added} cards to your collection!`);
      confetti({ particleCount: 150, spread: 90 });
      setQueue((q) => q.filter((x) => !ready.includes(x)));
    } catch (e) { toast.error(formatErr(e)); }
  };

  return (
    <div data-testid="scan-page">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl font-black tracking-tight sm:text-5xl">Scan cards</h1>
          <p className="mt-2 text-slate-600">Hold a card inside the frame. Recognition runs on your own server.</p>
        </div>
        <div className="flex rounded-full bg-white p-1 shadow-sm" data-testid="scan-mode-toggle">
          {["single", "batch"].map((m) => (
            <button key={m} onClick={() => { setMode(m); setRes(null); }} data-testid={`scan-mode-${m}`}
              className={`press rounded-full px-5 py-2 font-display font-bold capitalize ${mode === m ? "bg-slate-900 text-white" : "text-slate-600"}`}>{m === "batch" ? "Batch mode" : "Single"}</button>
          ))}
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,480px)_1fr]">
        <div className="space-y-4">
          <div className="relative mx-auto aspect-[3/4] w-full max-w-[480px] overflow-hidden rounded-[28px] bg-slate-900 shadow-[0_20px_50px_rgba(0,0,0,0.3)]" data-testid="camera-view">
            <video ref={videoRef} playsInline muted className="h-full w-full object-cover" />
            {cam !== "ready" && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-8 text-center text-white">
                <Camera className="h-10 w-10 opacity-70" />
                <p className="font-display text-lg font-bold" data-testid="camera-status">
                  {cam === "idle" ? "Starting camera…" : cam === "denied" ? "Camera permission denied" : "Live camera needs HTTPS or localhost"}
                </p>
                <p className="text-sm text-white/70">You can still take or upload photos below — they work everywhere.</p>
              </div>
            )}
            {cam === "ready" && (
              <div className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-2xl border-[3px] border-dashed border-white/80 shadow-[0_0_0_9999px_rgba(0,0,0,0.45)]"
                style={{ height: `${GUIDE_H * 100}%`, aspectRatio: "63/88" }}>
                {(busy || auto) && <div className="scan-beam" />}
              </div>
            )}
            {mode === "batch" && auto && <span className="absolute left-4 top-4 rounded-full bg-[#E3350D] px-3 py-1 text-xs font-black text-white">AUTO</span>}
          </div>
          <div className="flex flex-wrap justify-center gap-3">
            <Btn onClick={capture} disabled={cam !== "ready" || (mode === "single" && busy)} className="px-8 py-3 text-lg" data-testid="capture-button">
              <Camera className="h-5 w-5" /> {busy ? "Scanning…" : "Capture"}
            </Btn>
            {mode === "batch" && (
              <Btn variant={auto ? "yellow" : "ghost"} onClick={() => setAuto(!auto)} disabled={cam !== "ready"} data-testid="auto-scan-toggle"><Zap className="h-5 w-5" /> Auto {auto ? "on" : "off"}</Btn>
            )}
            <label className="press inline-flex cursor-pointer items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 font-display font-bold" data-testid="take-photo-button">
              <Upload className="h-5 w-5" /> Take photo
              <input type="file" accept="image/*" capture="environment" className="hidden" onChange={onFiles} data-testid="take-photo-input" />
            </label>
            <label className="press inline-flex cursor-pointer items-center gap-2 rounded-full border border-slate-200 bg-white px-5 py-2.5 font-display font-bold" data-testid="upload-photos-button">
              <Images className="h-5 w-5" /> Upload {mode === "batch" ? "photos" : "photo"}
              <input type="file" accept="image/*" multiple={mode === "batch"} className="hidden" onChange={onFiles} data-testid="upload-photos-input" />
            </label>
          </div>
          {mode === "single" && (
            <label className="flex items-center justify-center gap-2 text-sm font-semibold text-slate-600">
              <input type="checkbox" checked={autoOpen} onChange={(e) => setAutoOpen(e.target.checked)} data-testid="auto-open-checkbox" /> Open card page automatically when sure
            </label>
          )}
        </div>
        <div>
          {mode === "single" ? (
            busy ? <p className="animate-pulse font-display text-lg font-bold text-slate-500">Recognising card…</p> : <SingleResult res={res} onAdd={addOne} />
          ) : (
            <div className="space-y-3" data-testid="batch-queue">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-display text-xl font-bold">Scanned: {queue.length}</p>
                <div className="flex gap-2">
                  {queue.length > 0 && <Btn variant="ghost" onClick={() => setQueue([])} data-testid="batch-clear-button">Clear</Btn>}
                  <Btn onClick={addAll} disabled={!ready.length} data-testid="batch-add-all-button"><Check className="h-5 w-5" /> Add {ready.length} to collection</Btn>
                </div>
              </div>
              {queue.length === 0 && <p className="rounded-2xl border-2 border-dashed border-slate-200 p-8 text-center text-slate-500">Turn on <b>Auto</b> and slide cards under the camera one after another, or upload a bunch of photos at once.</p>}
              {queue.map((it) => <QueueItem key={it.key} it={it} onChange={(p) => patch(it.key, p)} onRemove={() => setQueue((q) => q.filter((x) => x.key !== it.key))} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
