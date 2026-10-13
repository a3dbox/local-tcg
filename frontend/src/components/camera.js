import { useEffect, useRef, useState } from "react";

export const GUIDE_H = 0.82;
const RATIO = 63 / 88;

export function useCamera(videoRef, deviceId) {
  const [state, setState] = useState("idle");
  const [caps, setCaps] = useState({});
  const [devices, setDevices] = useState([]);
  const trackRef = useRef(null);
  useEffect(() => {
    let stream;
    let cancelled = false;
    if (!navigator.mediaDevices?.getUserMedia || !window.isSecureContext) { setState("unsupported"); return; }
    const source = deviceId ? { deviceId: { exact: deviceId } } : { facingMode: { ideal: "environment" } };
    navigator.mediaDevices.getUserMedia({ video: { ...source, width: { ideal: 2560 }, height: { ideal: 1920 } }, audio: false })
      .then(async (s) => {
        if (cancelled) { s.getTracks().forEach((t) => t.stop()); return; }
        stream = s;
        const track = s.getVideoTracks()[0];
        trackRef.current = track;
        const c = track.getCapabilities?.() || {};
        if (c.focusMode?.includes("continuous")) track.applyConstraints({ advanced: [{ focusMode: "continuous" }] }).catch(() => {});
        setCaps(c);
        if (videoRef.current) { videoRef.current.srcObject = s; await videoRef.current.play().catch(() => {}); }
        setState("ready");
        const all = await navigator.mediaDevices.enumerateDevices().catch(() => []);
        setDevices(all.filter((d) => d.kind === "videoinput"));
      })
      .catch(() => setState("denied"));
    return () => { cancelled = true; stream?.getTracks().forEach((t) => t.stop()); };
  }, [videoRef, deviceId]);
  const apply = (c) => trackRef.current?.applyConstraints({ advanced: [c] }).catch(() => {});
  return { state, caps, devices, apply };
}

export function guideRect(video, margin = 1.1) {
  const vw = video?.videoWidth, vh = video?.videoHeight, cw = video?.clientWidth, ch = video?.clientHeight;
  if (!vw || !cw) return null;
  const scale = Math.max(cw / vw, ch / vh);
  const ox = (vw - cw / scale) / 2, oy = (vh - ch / scale) / 2;
  const gh = Math.min(ch, ch * GUIDE_H * margin), gw = Math.min(cw, gh * RATIO);
  return { sx: ox + (cw - gw) / 2 / scale, sy: oy + (ch - gh) / 2 / scale, sw: gw / scale, sh: gh / scale };
}

export function grabFrame(video) {
  const r = guideRect(video);
  if (!r) return null;
  const out = Math.min(1, 1600 / r.sh);
  const c = document.createElement("canvas");
  c.width = Math.round(r.sw * out); c.height = Math.round(r.sh * out);
  c.getContext("2d").drawImage(video, r.sx, r.sy, r.sw, r.sh, 0, 0, c.width, c.height);
  return new Promise((res) => c.toBlob(res, "image/jpeg", 0.92));
}

export function frameStats(gray, w, h, prev) {
  let motion = 0;
  if (prev) { for (let i = 0; i < gray.length; i++) motion += Math.abs(gray[i] - prev[i]); motion /= gray.length; }
  let sum = 0, sq = 0, n = 0;
  for (let y = 1; y < h - 1; y++) for (let x = 1; x < w - 1; x++) {
    const i = y * w + x;
    const l = 4 * gray[i] - gray[i - 1] - gray[i + 1] - gray[i - w] - gray[i + w];
    sum += l; sq += l * l; n++;
  }
  return { motion: prev ? motion : 999, sharpness: sq / n - (sum / n) ** 2 };
}

export function nextSteadyState(s, { motion, sharpness }, { moveT = 10, sharpT = 60, need = 3 } = {}) {
  if (motion > moveT) return { ...s, still: 0, armed: true, status: "moving", fire: false };
  if (!s.armed) return { ...s, status: "waiting", fire: false };
  if (sharpness < sharpT) return { ...s, still: 0, status: "blurry", fire: false };
  const still = s.still + 1;
  if (still >= need) return { still: 0, armed: false, status: "steady", fire: true };
  return { ...s, still, status: "steady", fire: false };
}

export function useSteady(videoRef, active, onSteady) {
  const [status, setStatus] = useState("idle");
  const cb = useRef(onSteady);
  cb.current = onSteady;
  useEffect(() => {
    if (!active) { setStatus("idle"); return undefined; }
    const W = 48, H = 66;
    const c = document.createElement("canvas");
    c.width = W; c.height = H;
    const ctx = c.getContext("2d", { willReadFrequently: true });
    let prev = null;
    let st = { still: 0, armed: true, status: "moving" };
    const t = setInterval(() => {
      const v = videoRef.current;
      const r = guideRect(v, 1);
      if (!r) return;
      ctx.drawImage(v, r.sx, r.sy, r.sw, r.sh, 0, 0, W, H);
      const d = ctx.getImageData(0, 0, W, H).data;
      const g = new Float32Array(W * H);
      for (let i = 0; i < g.length; i++) g[i] = d[i * 4] * 0.3 + d[i * 4 + 1] * 0.59 + d[i * 4 + 2] * 0.11;
      st = nextSteadyState(st, frameStats(g, W, H, prev));
      prev = g;
      setStatus(st.status);
      if (st.fire) cb.current();
    }, 220);
    return () => clearInterval(t);
  }, [active, videoRef]);
  return status;
}

export function beep() {
  try {
    const a = new (window.AudioContext || window.webkitAudioContext)();
    const o = a.createOscillator(), g = a.createGain();
    o.frequency.value = 880; g.gain.value = 0.08;
    o.connect(g); g.connect(a.destination); o.start(); o.stop(a.currentTime + 0.09);
  } catch { /* no audio */ }
}

export const STEADY_TEXT = {
  idle: "", moving: "Hold the card still inside the frame", blurry: "Too blurry — move a little further away or add light",
  steady: "Hold it… scanning", waiting: "Got it! Swap to the next card",
};
