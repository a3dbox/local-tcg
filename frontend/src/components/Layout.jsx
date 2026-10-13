import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Home, Search, Layers, ScanLine, LibraryBig, Target, Heart, BookOpen, Settings, LogOut, Menu, Users } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";

const NAV = [
  { to: "/", label: "Home", icon: Home, end: true },
  { to: "/search", label: "Search", icon: Search },
  { to: "/scan", label: "Scan", icon: ScanLine },
  { to: "/sets", label: "Sets", icon: Layers },
  { to: "/collection", label: "My Cards", icon: LibraryBig },
  { to: "/goals", label: "Goals", icon: Target },
  { to: "/wishlist", label: "Wishlist", icon: Heart },
  { to: "/family", label: "Family", icon: Users },
  { to: "/pokedex", label: "Pokédex", icon: BookOpen },
  { to: "/settings", label: "Settings", icon: Settings },
];
const MOBILE = ["/", "/search", "/scan", "/sets", "/collection"];

const Logo = () => (
  <div className="flex items-center gap-2" data-testid="app-logo">
    <div className="relative h-8 w-8 rounded-full border-[3px] border-slate-900 bg-[linear-gradient(#E3350D_50%,white_50%)]">
      <div className="absolute left-1/2 top-1/2 h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-[3px] border-slate-900 bg-white" />
    </div>
    <span className="font-display text-xl font-black tracking-tight">PokéBinder</span>
  </div>
);

function Sidebar({ user, logout }) {
  return (
    <aside className="sticky top-0 hidden h-screen w-64 shrink-0 flex-col border-r border-slate-200/70 bg-white/70 p-5 backdrop-blur-xl lg:flex">
      <Logo />
      <nav className="mt-8 flex flex-1 flex-col gap-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} data-testid={`nav-${label.toLowerCase().replace(/[^a-z]/g, "")}`}
            className={({ isActive }) => `press flex items-center gap-3 rounded-full px-4 py-2.5 font-display font-semibold ${isActive ? "bg-[#E3350D] text-white shadow-[0_4px_0_#B02808]" : "text-slate-600 hover:bg-slate-100"}`}>
            <Icon className="h-5 w-5" strokeWidth={2.5} /> {label}
          </NavLink>
        ))}
      </nav>
      <div className="rounded-2xl bg-slate-50 p-3">
        <p className="truncate font-display font-bold" data-testid="sidebar-user-name">{user?.name}</p>
        <p className="truncate text-xs text-slate-500">{user?.email}</p>
        <button onClick={logout} data-testid="logout-button" className="mt-2 flex items-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#E3350D]">
          <LogOut className="h-4 w-4" /> Log out
        </button>
      </div>
    </aside>
  );
}

function MobileTop({ logout }) {
  const nav = useNavigate();
  return (
    <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200/60 bg-white/80 px-4 py-3 backdrop-blur-xl lg:hidden">
      <Logo />
      <DropdownMenu>
        <DropdownMenuTrigger data-testid="mobile-menu-button" className="rounded-full p-2 hover:bg-slate-100"><Menu className="h-6 w-6" /></DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          {NAV.filter((n) => !MOBILE.includes(n.to)).map((n) => (
            <DropdownMenuItem key={n.to} onClick={() => nav(n.to)} data-testid={`mobile-nav-${n.label.toLowerCase().replace(/[^a-z]/g, "")}`}>
              <n.icon className="mr-2 h-4 w-4" /> {n.label}
            </DropdownMenuItem>
          ))}
          <DropdownMenuItem onClick={logout} data-testid="mobile-logout"><LogOut className="mr-2 h-4 w-4" /> Log out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}

function BottomNav() {
  return (
    <nav className="fixed inset-x-0 bottom-0 z-30 flex items-end justify-around border-t border-slate-200/50 bg-white/85 px-2 pb-3 pt-2 backdrop-blur-2xl lg:hidden">
      {NAV.filter((n) => MOBILE.includes(n.to)).map(({ to, label, icon: Icon, end }) =>
        to === "/scan" ? (
          <NavLink key={to} to={to} data-testid="bottom-nav-scan" className="press -mt-7 flex h-16 w-16 items-center justify-center rounded-full bg-[#E3350D] text-white shadow-[0_6px_0_#B02808]">
            <Icon className="h-7 w-7" strokeWidth={2.5} />
          </NavLink>
        ) : (
          <NavLink key={to} to={to} end={end} data-testid={`bottom-nav-${label.toLowerCase().replace(/[^a-z]/g, "")}`}
            className={({ isActive }) => `flex flex-col items-center gap-0.5 px-2 text-[11px] font-bold ${isActive ? "text-[#E3350D]" : "text-slate-500"}`}>
            <Icon className="h-6 w-6" strokeWidth={2.5} /> {label}
          </NavLink>
        )
      )}
    </nav>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  return (
    <div className="dot-bg flex min-h-screen">
      <Sidebar user={user} logout={logout} />
      <div className="min-w-0 flex-1">
        <MobileTop logout={logout} />
        <main className="mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 lg:px-10 lg:pb-12 lg:pt-10">
          <Outlet />
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
