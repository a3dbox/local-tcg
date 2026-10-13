import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Layout from "@/components/Layout";
import { Spinner } from "@/components/UI";
import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Search from "@/pages/Search";
import CardDetail from "@/pages/CardDetail";
import Sets from "@/pages/Sets";
import SetDetail from "@/pages/SetDetail";
import Collection from "@/pages/Collection";
import { Goals, Wishlist } from "@/pages/Goals";
import { Pokedex, PokemonCards } from "@/pages/Pokedex";
import Scan from "@/pages/Scan";
import Settings from "@/pages/Settings";
import Family from "@/pages/Family";

function Protected({ children }) {
  const { user } = useAuth();
  if (user === null) return <Spinner />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/search" element={<Search />} />
            <Route path="/card/:id" element={<CardDetail />} />
            <Route path="/sets" element={<Sets />} />
            <Route path="/sets/:id" element={<SetDetail />} />
            <Route path="/collection" element={<Collection />} />
            <Route path="/goals" element={<Goals />} />
            <Route path="/wishlist" element={<Wishlist />} />
            <Route path="/family" element={<Family />} />
            <Route path="/pokedex" element={<Pokedex />} />
            <Route path="/pokedex/:dex" element={<PokemonCards />} />
            <Route path="/scan" element={<Scan />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </AuthProvider>
  );
}
