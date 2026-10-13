import { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { formatErr } from "@/lib/api";
import { Btn } from "@/components/UI";

export default function Login() {
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  if (user) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(f.email, f.password);
      else await register(f.name, f.email, f.password);
    } catch (ex) {
      setErr(formatErr(ex));
    } finally {
      setBusy(false);
    }
  };
  const input = "w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-base outline-none focus:border-[#E3350D] focus:ring-2 focus:ring-[#E3350D]/20";

  return (
    <div className="dot-bg grid min-h-screen lg:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-[#E3350D] p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full border-[40px] border-white/10" />
        <div className="absolute -bottom-40 -left-20 h-[28rem] w-[28rem] rounded-full border-[50px] border-black/10" />
        <p className="font-display text-xl font-black">PokéBinder</p>
        <div className="relative">
          <h1 className="font-display text-6xl font-black leading-[0.95] tracking-tight">Catch every card.<br />Finish every set.</h1>
          <p className="mt-6 max-w-md text-lg text-white/85">Search every Pokémon card ever printed, scan your real cards in seconds, and see exactly what's left to complete your sets.</p>
        </div>
        <p className="text-sm text-white/70">Self-hosted · Card data by TCGdex</p>
      </div>
      <div className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="rise w-full max-w-md rounded-3xl border border-slate-200/60 bg-white p-8 shadow-[0_12px_40px_rgba(0,0,0,0.08)]" data-testid="auth-form">
          <h2 className="font-display text-3xl font-black">{mode === "login" ? "Welcome back, Trainer!" : "Create your binder"}</h2>
          <p className="mt-1 text-slate-600">{mode === "login" ? "Log in to your collection." : "Every account has its own collection."}</p>
          <div className="mt-6 space-y-3">
            {mode === "register" && (
              <input className={input} placeholder="Your name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="register-name-input" required />
            )}
            <input className={input} type="email" placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="auth-email-input" required />
            <input className={input} type="password" placeholder="Password" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} data-testid="auth-password-input" required />
          </div>
          {err && <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm font-semibold text-red-600" data-testid="auth-error">{err}</p>}
          <Btn type="submit" disabled={busy} className="mt-6 w-full py-3 text-lg" data-testid="auth-submit-button">
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </Btn>
          <button type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setErr(""); }}
            className="mt-4 w-full text-center text-sm font-bold text-slate-600 hover:text-[#E3350D]" data-testid="auth-toggle-mode">
            {mode === "login" ? "New here? Create an account" : "Already have an account? Log in"}
          </button>
        </form>
      </div>
    </div>
  );
}
