import { create } from "zustand";
import type { GameCard, GameState } from "../api/types";

type Pending = "mulligan" | "choice" | null;

interface GameStore {
  state: GameState | null;
  ws: WebSocket | null;
  pending: Pending;
  mulliganCards: number[];
  choiceCards: GameCard[];
  log: string[];
  lastEvent: { kind: string; source?: number; target?: number } | null;
  connect: (gameId: string, token: string) => void;
  send: (msg: unknown) => void;
  reset: () => void;
}

export const useGame = create<GameStore>((set, get) => ({
  state: null,
  ws: null,
  pending: null,
  mulliganCards: [],
  choiceCards: [],
  log: [],
  lastEvent: null,
  connect: (gameId, token) => {
    get().reset();
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${location.host}/api/games/${gameId}/ws?token=${encodeURIComponent(token)}`
    );
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === "snapshot") {
        set({ state: msg.state, pending: msg.state.pending?.kind ?? null });
      } else if (msg.type === "mulligan") {
        set({ pending: "mulligan", mulliganCards: msg.cards });
      } else if (msg.type === "choice") {
        set({ pending: "choice", choiceCards: msg.choice.cards });
      } else if (msg.type === "log") {
        set((s) => ({ log: [...s.log, msg.message].slice(-100) }));
      } else if (msg.type === "event") {
        set({ lastEvent: msg.event });
      } else if (msg.type === "game_over") {
        set({ pending: null });
      }
    };
    set({ ws });
  },
  send: (msg) => {
    const ws = get().ws;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(msg));
  },
  reset: () => {
    get().ws?.close();
    set({ ws: null, state: null, pending: null, mulliganCards: [], choiceCards: [], log: [], lastEvent: null });
  },
}));
