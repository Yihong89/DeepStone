import type { ReactNode } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import App from "./App";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Lobby from "./pages/Lobby";
import Gallery from "./pages/Gallery";
import DeckList from "./pages/DeckList";
import DeckBuilder from "./pages/DeckBuilder";
import Play from "./pages/Play";
import GameBoard from "./pages/GameBoard";
import { useAuth } from "./store/auth";

function RequireAuth({ children }: { children: ReactNode }) {
  const user = useAuth((s) => s.user);
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <RequireAuth><Lobby /></RequireAuth> },
      { path: "login", element: <Login /> },
      { path: "register", element: <Register /> },
      { path: "cards", element: <RequireAuth><Gallery /></RequireAuth> },
      { path: "decks", element: <RequireAuth><DeckList /></RequireAuth> },
      { path: "decks/:id", element: <RequireAuth><DeckBuilder /></RequireAuth> },
      { path: "play", element: <RequireAuth><Play /></RequireAuth> },
      { path: "game/:gameId", element: <RequireAuth><GameBoard /></RequireAuth> },
    ],
  },
]);
