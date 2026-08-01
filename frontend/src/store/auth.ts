import { create } from "zustand";
import { me } from "../api/client";
import type { User } from "../api/types";

interface AuthState {
  user: User | null;
  token: string | null;
  ready: boolean;
  setToken: (t: string | null) => void;
  setUser: (u: User | null) => void;
  bootstrap: () => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("deepcards_token"),
  ready: false,
  setToken: (t) => {
    if (t) localStorage.setItem("deepcards_token", t);
    else localStorage.removeItem("deepcards_token");
    set({ token: t });
  },
  setUser: (u) => set({ user: u }),
  bootstrap: async () => {
    const token = get().token;
    if (!token) {
      set({ ready: true });
      return;
    }
    try {
      const user = await me();
      set({ user, ready: true });
    } catch {
      get().setToken(null);
      set({ ready: true });
    }
  },
  logout: () => {
    get().setToken(null);
    set({ user: null });
  },
}));
