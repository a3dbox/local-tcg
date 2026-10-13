import axios from "axios";

export const API_BASE = `${process.env.REACT_APP_BACKEND_URL ?? ""}/api`;
export const api = axios.create({ baseURL: API_BASE });

export const saveTokens = (d) => {
  localStorage.setItem("pb_access", d.access_token);
  localStorage.setItem("pb_refresh", d.refresh_token);
};
export const clearTokens = () => {
  localStorage.removeItem("pb_access");
  localStorage.removeItem("pb_refresh");
};

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("pb_access");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

let refreshing = null;
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const orig = err.config;
    const skip = ["/auth/login", "/auth/register", "/auth/refresh"].some((p) => orig?.url?.includes(p));
    const rt = localStorage.getItem("pb_refresh");
    if (err.response?.status === 401 && !orig._retry && !skip && rt) {
      orig._retry = true;
      try {
        refreshing = refreshing || axios.post(`${API_BASE}/auth/refresh`, { refresh_token: rt });
        const { data } = await refreshing;
        saveTokens(data);
        return api(orig);
      } catch {
        clearTokens();
        window.location.href = "/login";
      } finally {
        refreshing = null;
      }
    }
    return Promise.reject(err);
  }
);

export function formatErr(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong. Please try again.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export const cardImg = (image, q = "low") => (image ? `${image}/${q}.webp` : null);
export const logoImg = (logo) => (logo ? `${logo}.webp` : null);
export const usd = (v) => (v == null ? "—" : `$${Number(v).toFixed(2)}`);
export const eur = (v) => (v == null ? "—" : `€${Number(v).toFixed(2)}`);
export const VARIANT_LABELS = { normal: "Normal", holo: "Holo", reverse: "Reverse Holo", firstEdition: "1st Edition", wPromo: "W Promo" };
export const vLabel = (v) => VARIANT_LABELS[v] || v;
export const TYPE_COLORS = {
  Grass: "#4ADE80", Fire: "#F87171", Water: "#60A5FA", Lightning: "#FACC15", Psychic: "#C084FC",
  Fighting: "#FB923C", Darkness: "#475569", Metal: "#94A3B8", Fairy: "#F9A8D4", Dragon: "#C8A951", Colorless: "#E2E8F0",
};
export const artwork = (id) => `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/${id}.png`;
